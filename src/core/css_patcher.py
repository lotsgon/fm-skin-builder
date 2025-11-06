from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any, Set
from types import SimpleNamespace
import re
import json
import os
import shutil
import UnityPy

try:
    from UnityPy.classes.math import ColorRGBA as UnityColorRGBA
except Exception:  # pragma: no cover - UnityPy may not expose ColorRGBA in tests
    UnityColorRGBA = None

from .logger import get_logger
import gc
from .cache import load_or_cache_config, cache_dir
from .context import BundleContext, PatchReport
from .services import (
    CssPatchOptions,
    CssPatchService,
    TextureSwapOptions,
    TextureSwapService,
)
from .css_utils import (
    build_selector_from_parts,
    clean_for_json,
    hex_to_rgba,
    load_css_selector_overrides,
    load_css_vars,
    serialize_stylesheet_to_uss,
)
from .texture_utils import (
    collect_replacement_stems,
    gather_texture_names_from_index,
    load_texture_name_map,
    should_swap_textures,
)
from .scan_cache import (
    load_or_refresh_candidates as _load_or_refresh_scan_cache,
    load_cached_bundle_index,
)
from .css_sources import collect_css_from_dir, load_targeting_hints
from .bundle_paths import infer_bundle_files

log = get_logger(__name__)
# -----------------------------
# Core patcher
# -----------------------------


def _build_unity_color(colors: Iterable[Any], r: float, g: float, b: float, a: float) -> Any:
    """Create a Unity-compatible color instance, falling back to simple namespaces for tests."""
    if UnityColorRGBA is not None:
        try:
            return UnityColorRGBA(r, g, b, a)
        except Exception:
            pass

    sample = next(iter(colors), None)
    if sample is not None:
        cls = type(sample)
        try:
            return cls(r, g, b, a)  # type: ignore[call-arg]
        except Exception:
            instance = cls()  # type: ignore[call-arg]
            for attr, value in ("r", r), ("g", g), ("b", b), ("a", a):
                setattr(instance, attr, value)
            return instance

    # Fallback for empty color arrays in unit tests
    color = SimpleNamespace()
    color.r, color.g, color.b, color.a = r, g, b, a
    return color


class CssPatcher:
    def __init__(
        self,
        css_vars: Dict[str, str],
        selector_overrides: Dict[Tuple[str, str], str],
        patch_direct: bool = False,
        debug_export_dir: Optional[Path] = None,
        dry_run: bool = False,
        selectors_filter: Optional[Set[str]] = None,
        selector_props_filter: Optional[Set[Tuple[str, str]]] = None,
    ) -> None:
        self.css_vars = css_vars
        self.selector_overrides = selector_overrides
        self.patch_direct = patch_direct
        self.debug_export_dir = debug_export_dir
        self.dry_run = dry_run
        # Optional targeting hints (advanced)
        # If provided, limit selector/property override application to these filters.
        # selectors_filter contains selector strings (with or without leading '.')
        # selector_props_filter contains (selector, property) tuples (selector can be with or without '.')
        self.selectors_filter = selectors_filter
        self.selector_props_filter = selector_props_filter

    def patch_bundle_file(self, bundle_path: Path, out_dir: Path, candidate_assets: Optional[Set[str]] = None) -> Optional[List[str]]:
        bundle_context = BundleContext(bundle_path, loader=UnityPy.load)
        try:
            report = self.patch_bundle(
                bundle_context, candidate_assets=candidate_assets)
            if not report.has_changes:
                return report.summary_lines if self.dry_run else None
            if self.dry_run:
                return report.summary_lines

            saved_path = bundle_context.save_modified(
                out_dir, dry_run=self.dry_run)
            if saved_path is None:
                log.error(
                    "[ERROR] Could not save patched bundle. The bundle may be corrupt or use unsupported compression."
                )
                return None

            report.mark_saved(saved_path)
            log.info(f"💾 Saved patched bundle(s) → {out_dir}")
            return None
        finally:
            bundle_context.dispose()

    def patch_bundle(
        self,
        bundle: BundleContext,
        candidate_assets: Optional[Set[str]] = None,
    ) -> PatchReport:
        bundle.load()
        bundle_name = bundle.bundle_path.name
        env = bundle.env

        patched_vars = 0
        patched_direct = 0
        found_styles = 0
        any_changes = False
        changed_asset_names: Set[str] = set()
        report = PatchReport(bundle.bundle_path, dry_run=self.dry_run)
        self._selector_touches = {}

        log.info(f"🔍 Scanning bundle: {bundle_name}")

        original_uss: List[Tuple[Any, Any, str]] = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            data = obj.read()
            if not hasattr(data, "colors") or not hasattr(data, "strings"):
                continue
            name = getattr(data, "m_Name", "UnnamedStyleSheet")
            if candidate_assets is not None and name not in candidate_assets:
                continue
            will_patch = self._will_patch(data)
            if self.debug_export_dir and will_patch and not self.dry_run:
                self.debug_export_dir.mkdir(parents=True, exist_ok=True)
                self._export_debug_original(name, data)
            original_uss.append((obj, data, name))

        for obj, data, name in original_uss:
            found_styles += 1
            pv, pd, changed = self._apply_patches_to_stylesheet(name, data)
            patched_vars += pv
            patched_direct += pd
            if changed:
                any_changes = True
                changed_asset_names.add(name)
                if not self.dry_run:
                    data.save()

        if not any_changes:
            log.info(
                "No changes detected; skipping bundle write and debug outputs.")
            try:
                original_uss.clear()
            except Exception:
                pass
            report.variables_patched = patched_vars
            report.direct_patched = patched_direct
            return report

        if not self.dry_run:
            bundle.mark_dirty()

        multi_asset_touches: List[Tuple[Tuple[str, str], int]] = []
        for k, assets in getattr(self, "_selector_touches", {}).items():
            if isinstance(assets, set) and len(assets) > 1:
                multi_asset_touches.append((k, len(assets)))

        report.assets_modified = changed_asset_names
        report.variables_patched = patched_vars
        report.direct_patched = patched_direct
        report.selector_conflicts = [
            (sel, prop, count) for (sel, prop), count in multi_asset_touches
        ]

        if self.dry_run:
            lines: List[str] = []
            lines.append("\n🧾 Summary:")
            lines.append(f"  Stylesheets found: {found_styles}")
            lines.append(f"  Assets modified: {len(changed_asset_names)}")
            lines.append(f"  Variables patched: {patched_vars}")
            lines.append(f"  Direct colors patched: {patched_direct}")
            if multi_asset_touches:
                lines.append("  Selector overrides affecting multiple assets:")
                for (sel, prop), n in multi_asset_touches:
                    lines.append(f"    {sel} / {prop}: {n} assets")
            lines.append(
                "[DRY-RUN] No files were written. Use without --dry-run to apply changes."
            )
            report.summary_lines = lines
        else:
            log.info("\n🧾 Summary:")
            log.info(f"  Stylesheets found: {found_styles}")
            log.info(f"  Assets modified: {len(changed_asset_names)}")
            log.info(f"  Variables patched: {patched_vars}")
            log.info(f"  Direct colors patched: {patched_direct}")
            if multi_asset_touches:
                log.info("  Selector overrides affecting multiple assets:")
                for (sel, prop), n in multi_asset_touches:
                    log.info(f"    {sel} / {prop}: {n} assets")

        if self.debug_export_dir and not self.dry_run:
            log.info(f"📝 Exported .uss files to {self.debug_export_dir}")

        try:
            original_uss.clear()
        except Exception:
            pass

        return report

    # -----------------------------
    # internals
    # -----------------------------

    def _will_patch(self, data) -> bool:
        # Check var-based direct property patches
        for rule in getattr(data, "m_Rules", []):
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                # Be permissive: try raw, stripped, and prefixed forms so
                # bundle property names that differ by leading dashes still match
                prop_candidates = []
                if prop_name is not None:
                    prop_candidates = [prop_name, prop_name.lstrip(
                        "-"), "--" + prop_name.lstrip("-")]
                match_key = next(
                    (k for k in prop_candidates if k in self.css_vars), None)
                if match_key:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(getattr(data, "colors", [])):
                                hex_val = self.css_vars[match_key]
                                r, g, b, a = hex_to_rgba(hex_val)
                                col = data.colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                    return True

        # Check for root-level variables that currently reference other tokens (no literal color yet)
        for rule in getattr(data, "m_Rules", []):
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if not prop_name:
                    continue
                candidates = [prop_name, prop_name.lstrip(
                    "-"), "--" + prop_name.lstrip("-")]
                match_key = next(
                    (k for k in candidates if k in self.css_vars), None)
                if not match_key:
                    continue
                has_literal_color = any(
                    getattr(val, "m_ValueType", None) == 4 for val in getattr(prop, "m_Values", [])
                )
                if not has_literal_color:
                    return True

        # Check strict CSS variable mapping: both string (type 3/10) and color (type 4) on same index
        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        rules = getattr(data, "m_Rules", [])
        for color_idx in range(len(colors)):
            if color_idx >= len(strings):
                continue
            var_name = strings[color_idx]
            if var_name not in self.css_vars:
                continue
            found = False
            for rule in rules:
                for prop in getattr(rule, "m_Properties", []):
                    has_var = False
                    has_color = False
                    for val in getattr(prop, "m_Values", []):
                        vt = getattr(val, "m_ValueType", None)
                        vi = getattr(val, "valueIndex", None)
                        if vt in (3, 10) and vi == color_idx:
                            has_var = True
                        if vt == 4 and vi == color_idx:
                            has_color = True
                    if has_var and has_color:
                        found = True
                        break
                if found:
                    break
            if found:
                # Only consider a change if the target differs from current color
                target = self.css_vars.get(var_name)
                if target:
                    tr, tg, tb, ta = hex_to_rgba(target)
                    col = colors[color_idx]
                    if (col.r, col.g, col.b, col.a) != (tr, tg, tb, ta):
                        return True

        # Additional: consider root-level variable definitions where the strings array
        # names a CSS variable but there is no property that explicitly contains
        # both the string and a color value at that index. In those cases we still
        # want to patch the color entry itself so variable references elsewhere
        # pick up the new colour.
        for color_idx in range(len(colors)):
            if color_idx >= len(strings):
                continue
            var_name = strings[color_idx]
            # Try both raw and leading-dash-normalised forms
            candidates = [var_name, ("--" + var_name.lstrip("-"))]
            found_val = None
            for cand in candidates:
                if cand in self.css_vars:
                    found_val = self.css_vars[cand]
                    break
            if not found_val:
                continue
            tr, tg, tb, ta = hex_to_rgba(found_val)
            col = colors[color_idx]
            if (col.r, col.g, col.b, col.a) != (tr, tg, tb, ta):
                return True

        # Check direct literal patch
        if self.patch_direct and hasattr(data, "m_Rules"):
            for rule in getattr(data, "m_Rules", []):
                for prop in getattr(rule, "m_Properties", []):
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(getattr(data, "colors", [])):
                                prop_name = getattr(prop, "m_Name", "")
                                css_match = next(
                                    (self.css_vars[k] for k in self.css_vars if k.endswith(prop_name)), None)
                                if css_match:
                                    r, g, b, a = hex_to_rgba(css_match)
                                    col = data.colors[value_index]
                                    if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                        return True

        # Selector/property overrides
        selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
            data, "m_ComplexSelectors") else []
        rules = getattr(data, "m_Rules", [])
        for rule_idx, rule in enumerate(rules):
            selector_texts: List[str] = []
            for sel in selectors:
                if hasattr(sel, "ruleIndex") and getattr(sel, "ruleIndex", -1) == rule_idx:
                    for selector in getattr(sel, "m_Selectors", []):
                        parts = getattr(selector, "m_Parts", [])
                        selector_texts.append(build_selector_from_parts(parts))
            if not selector_texts:
                selector_texts = [f".rule-{rule_idx}", f"rule-{rule_idx}"]
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                for selector_text in selector_texts:
                    # Apply optional selector/selector+prop filters if present
                    sel_variants = [selector_text, selector_text.lstrip(".")]
                    if self.selector_props_filter is not None:
                        # Require a (selector, prop) match in hints
                        allowed = any(
                            (sv, prop_name) in self.selector_props_filter for sv in sel_variants)
                        if not allowed:
                            continue
                    elif self.selectors_filter is not None:
                        # Require selector to be in allowed set
                        allowed = any(
                            sv in self.selectors_filter for sv in sel_variants)
                        if not allowed:
                            continue

                    if (selector_text, prop_name) in self.selector_overrides or (
                        selector_text.lstrip("."), prop_name
                    ) in self.selector_overrides:
                        for val in getattr(prop, "m_Values", []):
                            if getattr(val, "m_ValueType", None) == 4:
                                value_index = getattr(val, "valueIndex", None)
                                if value_index is not None and 0 <= value_index < len(getattr(data, "colors", [])):
                                    return True
        return False

    def _apply_patches_to_stylesheet(self, name: str, data) -> Tuple[int, int, bool]:
        patched_vars = 0
        patched_direct = 0
        changed = False

        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        rules = getattr(data, "m_Rules", [])
        selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
            data, "m_ComplexSelectors") else []

        # Direct property patches (by var name == prop m_Name)
        direct_property_patched_indices = set()
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                # Normalize prop name variants to be permissive when matching keys
                match_key = None
                if prop_name is not None:
                    candidates = [prop_name, prop_name.lstrip(
                        "-"), "--" + prop_name.lstrip("-")]
                    match_key = next(
                        (k for k in candidates if k in self.css_vars), None)
                if match_key:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(colors):
                                hex_val = self.css_vars[match_key]
                                r, g, b, a = hex_to_rgba(hex_val)
                                col = colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                    col.r, col.g, col.b, col.a = r, g, b, a
                                    patched_vars += 1
                                    direct_property_patched_indices.add(
                                        value_index)
                                    log.info(
                                        f"  [PATCHED - direct property] {name}: {match_key} (color index {value_index}) → {hex_val}"
                                    )
                                    changed = True

        # If a root-level variable only references other tokens (e.g. var(--foo)) and the user
        # supplies a color override, convert that definition into a literal color so the new
        # value survives in the bundle even without updating the referenced token.
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if prop_name is None:
                    continue
                candidates = [prop_name, prop_name.lstrip(
                    "-"), "--" + prop_name.lstrip("-")]
                match_key = next(
                    (k for k in candidates if k in self.css_vars), None)
                if not match_key:
                    continue
                values = list(getattr(prop, "m_Values", []))
                has_literal_color = any(
                    getattr(val, "m_ValueType", None) == 4 for val in values)
                if has_literal_color or not values:
                    continue

                hex_val = self.css_vars[match_key]
                r, g, b, a = hex_to_rgba(hex_val)
                new_color = _build_unity_color(colors, r, g, b, a)
                colors.append(new_color)
                new_index = len(colors) - 1

                handle = next(
                    (val for val in values if getattr(
                        val, "m_ValueType", None) in {3, 8, 10}),
                    values[0],
                )
                setattr(handle, "m_ValueType", 4)
                setattr(handle, "valueIndex", new_index)

                patched_vars += 1
                direct_property_patched_indices.add(new_index)
                changed = True
                log.info(
                    f"  [PATCHED - var literal] {name}: {match_key} (new color index {new_index}) → {hex_val}"
                )

        # Strict CSS variable patching
        color_indices_to_patch: Dict[int, str] = {}
        for color_idx in range(len(colors)):
            if color_idx in direct_property_patched_indices:
                continue
            if color_idx >= len(strings):
                continue
            var_name = strings[color_idx]
            if var_name not in self.css_vars:
                continue
            found = False
            for rule in rules:
                for prop in getattr(rule, "m_Properties", []):
                    has_var = False
                    has_color = False
                    for val in getattr(prop, "m_Values", []):
                        vt = getattr(val, "m_ValueType", None)
                        vi = getattr(val, "valueIndex", None)
                        if vt in (3, 10) and vi == color_idx:
                            has_var = True
                        if vt == 4 and vi == color_idx:
                            has_color = True
                    if has_var and has_color:
                        found = True
                        break
                if found:
                    break
            if found:
                color_indices_to_patch[color_idx] = var_name
                log.info(
                    f"  [WILL PATCH] {name}: {var_name} (color index {color_idx}) → {self.css_vars[var_name]}")

        for color_idx, var_name in color_indices_to_patch.items():
            hex_val = self.css_vars.get(var_name)
            if not hex_val:
                continue
            r, g, b, a = hex_to_rgba(hex_val)
            col = colors[color_idx]
            if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                col.r, col.g, col.b, col.a = r, g, b, a
                patched_vars += 1
                log.info(
                    f"  [PATCHED] {name}: {var_name} (color index {color_idx}) → {hex_val}")
                changed = True

        # Optional: patch inlined literals
        if self.patch_direct:
            for rule in rules:
                for prop in getattr(rule, "m_Properties", []):
                    for val in getattr(prop, "m_Values", []):
                        value_type = getattr(val, "m_ValueType", None)
                        value_index = getattr(val, "valueIndex", None)
                        if value_type == 4 and 0 <= value_index < len(colors):
                            prop_name = getattr(prop, "m_Name", "")
                            css_match = next(
                                (self.css_vars[k] for k in self.css_vars if k.endswith(prop_name)), None)
                            if css_match:
                                r, g, b, a = hex_to_rgba(css_match)
                                col = colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                    col.r, col.g, col.b, col.a = r, g, b, a
                                    patched_direct += 1
                                    log.info(
                                        f"  [PATCHED] {name}: {prop_name} (index {value_index}) → {css_match}"
                                    )
                                    changed = True

        # Selector/property overrides
        for rule_idx, rule in enumerate(rules):
            selector_texts: List[str] = []
            for sel in selectors:
                if hasattr(sel, "ruleIndex") and getattr(sel, "ruleIndex", -1) == rule_idx:
                    for selector in getattr(sel, "m_Selectors", []):
                        parts = getattr(selector, "m_Parts", [])
                        selector_texts.append(build_selector_from_parts(parts))
            if not selector_texts:
                selector_texts = [f".rule-{rule_idx}", f"rule-{rule_idx}"]
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                for selector_text in selector_texts:
                    keys_to_try = [
                        (selector_text, prop_name),
                        (selector_text.lstrip("."), prop_name),
                    ]
                    for key in keys_to_try:
                        # Apply optional selector/selector+prop filters if present
                        if self.selector_props_filter is not None:
                            if key not in self.selector_props_filter:
                                continue
                        elif self.selectors_filter is not None:
                            sel_only = key[0]
                            if sel_only not in self.selectors_filter and sel_only.lstrip(".") not in self.selectors_filter:
                                continue
                        if key in self.selector_overrides:
                            hex_val = self.selector_overrides[key]
                            log.info(
                                f"  [DEBUG] Selector/property match: {key} in {name}, patching to {hex_val}"
                            )
                            values = list(getattr(prop, "m_Values", []))
                            r, g, b, a = hex_to_rgba(hex_val)
                            found_type4 = False
                            for val in values:
                                if getattr(val, "m_ValueType", None) == 4:
                                    found_type4 = True
                                    value_index = getattr(
                                        val, "valueIndex", None)
                                    if value_index is not None and 0 <= value_index < len(colors):
                                        col = colors[value_index]
                                        if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                            col.r, col.g, col.b, col.a = r, g, b, a
                                            patched_vars += 1
                                            log.info(
                                                f"  [PATCHED - selector/property] {name}: {key} (color index {value_index}) → {hex_val}"
                                            )
                                            changed = True
                                        else:
                                            log.info(
                                                f"  [PATCHED - selector/property] {name}: {key} (color index {value_index}) already set to {hex_val}"
                                            )
                                        try:
                                            touches = getattr(
                                                self, "_selector_touches", None)
                                            if touches is not None:
                                                norm_sel = key[0]
                                                touches.setdefault((norm_sel if norm_sel.startswith(
                                                    '.') else norm_sel, prop_name), set()).add(name)
                                        except Exception:
                                            pass
                            if not found_type4:
                                replacement_handle = next(
                                    (
                                        val
                                        for val in values
                                        if getattr(val, "m_ValueType", None) in {3, 8, 10}
                                    ),
                                    None,
                                )
                                if replacement_handle is None:
                                    log.warning(
                                        f"  [WARN] No suitable value found to convert for {key} in {name}."
                                    )
                                    continue
                                new_color = _build_unity_color(
                                    colors, r, g, b, a)
                                colors.append(new_color)
                                new_index = len(colors) - 1
                                setattr(replacement_handle, "m_ValueType", 4)
                                setattr(replacement_handle,
                                        "valueIndex", new_index)
                                patched_vars += 1
                                direct_property_patched_indices.add(new_index)
                                changed = True
                                log.info(
                                    f"  [PATCHED - selector/property literal] {name}: {key} (new color index {new_index}) → {hex_val}"
                                )
                                try:
                                    touches = getattr(
                                        self, "_selector_touches", None)
                                    if touches is not None:
                                        norm_sel = key[0]
                                        touches.setdefault((norm_sel if norm_sel.startswith(
                                            '.') else norm_sel, prop_name), set()).add(name)
                                except Exception:
                                    pass

        if self.debug_export_dir and changed and not self.dry_run:
            # Ensure dir exists before exporting
            self.debug_export_dir.mkdir(parents=True, exist_ok=True)
            self._export_debug_patched(name, data)

        return patched_vars, patched_direct, changed

    def _export_debug_original(self, name: str, data) -> None:
        assert self.debug_export_dir is not None
        uss_text = serialize_stylesheet_to_uss(data)
        (self.debug_export_dir /
         f"original_{name}.uss").write_text(uss_text, encoding="utf-8")

        try:
            raw_json = clean_for_json(data)
            root_fields = [
                "m_Name",
                "m_Script",
                "m_Enabled",
                "m_GameObject",
                "m_CorrespondingSourceObject",
                "m_EditorClassIdentifier",
                "m_EditorHideFlags",
                "m_HideFlags",
                "m_PrefabAsset",
                "m_PrefabInstance",
            ]
            out_json = {}
            for k in root_fields:
                if k in raw_json:
                    out_json[k] = raw_json[k]
                else:
                    if k in {"m_CorrespondingSourceObject", "m_PrefabAsset", "m_PrefabInstance", "m_GameObject"}:
                        out_json[k] = {"m_FileID": 0, "m_PathID": 0}
                    elif k == "m_EditorClassIdentifier":
                        out_json[k] = ""
                    elif k in {"m_EditorHideFlags", "m_HideFlags"}:
                        out_json[k] = 0
            structure = {k: raw_json[k]
                         for k in raw_json if k not in root_fields}
            if "m_ImportedWithWarnings" in structure and structure["m_ImportedWithWarnings"] is None:
                structure["m_ImportedWithWarnings"] = 0
            out_json["m_Structure"] = structure
            (self.debug_export_dir / f"original_{name}.json").write_text(
                json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            log.warning(
                f"[WARN] Could not export original JSON for {name}: {e}")

        minimal = {
            "m_Name": getattr(data, "m_Name", None),
            "strings": list(getattr(data, "strings", [])),
            "colors": [
                {"r": c.r, "g": c.g, "b": c.b, "a": c.a} for c in getattr(data, "colors", [])
            ],
        }
        (self.debug_export_dir / f"original_{name}_minimal.json").write_text(
            json.dumps(minimal, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _export_debug_patched(self, name: str, data) -> None:
        assert self.debug_export_dir is not None
        uss_text = serialize_stylesheet_to_uss(data)
        (self.debug_export_dir /
         f"patched_{name}.uss").write_text(uss_text, encoding="utf-8")
        try:
            raw_json = clean_for_json(data)
            root_fields = [
                "m_Name",
                "m_Script",
                "m_Enabled",
                "m_GameObject",
                "m_CorrespondingSourceObject",
                "m_EditorClassIdentifier",
                "m_EditorHideFlags",
                "m_HideFlags",
                "m_PrefabAsset",
                "m_PrefabInstance",
            ]
            out_json = {}
            for k in root_fields:
                if k in raw_json:
                    out_json[k] = raw_json[k]
                else:
                    if k in {"m_CorrespondingSourceObject", "m_PrefabAsset", "m_PrefabInstance", "m_GameObject"}:
                        out_json[k] = {"m_FileID": 0, "m_PathID": 0}
                    elif k == "m_EditorClassIdentifier":
                        out_json[k] = ""
                    elif k in {"m_EditorHideFlags", "m_HideFlags"}:
                        out_json[k] = 0
            structure = {k: raw_json[k]
                         for k in raw_json if k not in root_fields}
            if "m_ImportedWithWarnings" in structure and structure["m_ImportedWithWarnings"] is None:
                structure["m_ImportedWithWarnings"] = 0
            out_json["m_Structure"] = structure
            (self.debug_export_dir / f"patched_{name}.json").write_text(
                json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            log.warning(
                f"[WARN] Could not export patched JSON for {name}: {e}")
        minimal = {
            "m_Name": getattr(data, "m_Name", None),
            "strings": list(getattr(data, "strings", [])),
            "colors": [
                {"r": c.r, "g": c.g, "b": c.b, "a": c.a} for c in getattr(data, "colors", [])
            ],
        }
        (self.debug_export_dir / f"patched_{name}_minimal.json").write_text(
            json.dumps(minimal, ensure_ascii=False, indent=2), encoding="utf-8"
        )


@dataclass
class PipelineOptions:
    patch_direct: bool = False
    debug_export: bool = False
    backup: bool = False
    dry_run: bool = False
    use_scan_cache: bool = True
    refresh_scan_cache: bool = False


@dataclass
class PipelineResult:
    bundle_reports: List[PatchReport]
    css_bundles_modified: int
    texture_replacements_total: int
    texture_bundles_written: int
    bundles_requested: int
    summary_lines: List[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "PipelineResult":
        return cls(
            bundle_reports=[],
            css_bundles_modified=0,
            texture_replacements_total=0,
            texture_bundles_written=0,
            bundles_requested=0,
            summary_lines=[],
        )


class SkinPatchPipeline:
    """Coordinates CSS + texture patching for a skin directory."""

    def __init__(self, css_dir: Path, out_dir: Path, options: PipelineOptions) -> None:
        self.css_dir = css_dir
        self.out_dir = out_dir
        self.options = options

    def run(self, bundle: Optional[Path] = None) -> PipelineResult:
        css_vars, selector_overrides = collect_css_from_dir(self.css_dir)
        cfg_model = None
        cfg_path = self.css_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg_model = load_or_cache_config(self.css_dir)
            except Exception as e:
                log.warning(f"Could not parse config.json: {e}")

        hints_assets, hints_selectors, hints_selector_props = load_targeting_hints(
            self.css_dir
        )
        debug_dir = (self.out_dir /
                     "debug_uss") if self.options.debug_export else None
        css_service = CssPatchService(
            css_vars,
            selector_overrides,
            CssPatchOptions(
                patch_direct=self.options.patch_direct,
                debug_export_dir=debug_dir,
                dry_run=self.options.dry_run,
                selectors_filter=hints_selectors,
                selector_props_filter=hints_selector_props,
            ),
        )

        bundle_files: List[Path] = []
        if bundle is not None:
            if bundle.is_dir():
                bundle_files = [
                    p for p in bundle.iterdir() if p.suffix == ".bundle"]
            else:
                bundle_files = [bundle]
        else:
            bundle_files = infer_bundle_files(self.css_dir)
            if not bundle_files:
                log.error(
                    "No bundle specified and none could be inferred from config. Provide --bundle."
                )
                return PipelineResult.empty()

        bundles_requested = len(bundle_files)

        skin_is_known = (self.css_dir / "config.json").exists()
        cache_candidates: Dict[Path, Optional[Set[str]]] = {}
        skin_cache_dir: Optional[Path] = None
        if self.options.use_scan_cache and skin_is_known:
            try:
                skin_cache_dir = cache_dir(
                    root=self.css_dir.parent.parent) / self.css_dir.name
                skin_cache_dir.mkdir(parents=True, exist_ok=True)
                for b in bundle_files:
                    cand = _load_or_refresh_scan_cache(
                        skin_cache_dir,
                        self.css_dir,
                        b,
                        refresh=self.options.refresh_scan_cache,
                        css_vars=css_vars,
                        selector_overrides=selector_overrides,
                        patch_direct=self.options.patch_direct,
                    )
                    cache_candidates[b] = cand
            except Exception as e:
                log.debug(f"Scan cache unavailable: {e}")
                skin_cache_dir = None

        includes = getattr(cfg_model, "includes", None)
        includes_list: List[str] = list(
            includes) if isinstance(includes, list) else []
        want_icons = any(x.strip().lower() ==
                         "assets/icons" for x in includes_list)
        want_bgs = any(x.strip().lower() ==
                       "assets/backgrounds" for x in includes_list)
        icon_dir = self.css_dir / "assets" / "icons"
        bg_dir = self.css_dir / "assets" / "backgrounds"
        replace_stems = set(
            collect_replacement_stems(icon_dir) +
            collect_replacement_stems(bg_dir)
        )
        name_map = load_texture_name_map(self.css_dir)
        target_names_from_map = set(name_map.keys())

        swap_targets_present = any(
            x.strip().lower() in {"assets/icons", "assets/backgrounds"}
            for x in includes_list
        )
        texture_service: Optional[TextureSwapService] = None
        if swap_targets_present:
            texture_service = TextureSwapService(
                TextureSwapOptions(includes=includes_list,
                                   dry_run=self.options.dry_run)
            )

        summary_lines: List[str] = []
        bundle_reports: List[PatchReport] = []
        css_bundles_modified = 0
        texture_replacements_total = 0
        texture_bundles_written = 0

        for bundle_path in bundle_files:
            report = self._process_bundle(
                bundle_path,
                css_service=css_service,
                texture_service=texture_service,
                cache_candidates=cache_candidates,
                hints_assets=hints_assets,
                skin_cache_dir=skin_cache_dir,
                target_names_from_map=target_names_from_map,
                replace_stems=replace_stems,
                want_icons=want_icons,
                want_bgs=want_bgs,
            )

            if report is None:
                continue

            if report.summary_lines:
                summary_lines.extend(report.summary_lines)

            if report.assets_modified:
                css_bundles_modified += 1

            texture_replacements_total += report.texture_replacements
            if not self.options.dry_run and report.texture_replacements > 0:
                texture_bundles_written += 1

            bundle_reports.append(report)

        return PipelineResult(
            bundle_reports=bundle_reports,
            css_bundles_modified=css_bundles_modified,
            texture_replacements_total=texture_replacements_total,
            texture_bundles_written=texture_bundles_written,
            bundles_requested=bundles_requested,
            summary_lines=summary_lines,
        )

    def _process_bundle(
        self,
        bundle_path: Path,
        *,
        css_service: CssPatchService,
        texture_service: Optional[TextureSwapService],
        cache_candidates: Dict[Path, Optional[Set[str]]],
        hints_assets: Optional[Set[str]],
        skin_cache_dir: Optional[Path],
        target_names_from_map: Set[str],
        replace_stems: Set[str],
        want_icons: bool,
        want_bgs: bool,
    ) -> Optional[PatchReport]:
        if self.options.backup:
            ts = os.environ.get("FM_SKIN_BACKUP_TS") or "backup"
            backup_path = bundle_path.with_suffix(
                bundle_path.suffix + f".{ts}.bak")
            try:
                shutil.copy2(bundle_path, backup_path)
                log.info(f"🗄️ Backed up original bundle to {backup_path}")
            except Exception as exc:
                log.warning(f"Could not backup {bundle_path}: {exc}")

        log.info(f"\n=== Patching bundle: {bundle_path} ===")

        candidate_assets = cache_candidates.get(bundle_path)
        if hints_assets:
            if candidate_assets is None:
                candidate_assets = set(hints_assets)
            else:
                candidate_assets = set(candidate_assets) & set(hints_assets)

        if candidate_assets is not None and len(candidate_assets) == 0:
            log.info(
                f"Hint filter excluded all assets for {bundle_path.name}; skipping bundle."
            )
            return None

        do_css = True
        bundle_name_lower = bundle_path.name.lower()
        bundle_index: Optional[Dict[str, Any]] = None
        if self.options.refresh_scan_cache or self.options.use_scan_cache:
            if "styles" not in bundle_name_lower:
                bundle_index = load_cached_bundle_index(
                    self.css_dir,
                    bundle_path,
                    skin_cache_dir=skin_cache_dir,
                )
                if (bundle_index is None) or (not bundle_index.get("assets")):
                    do_css = False

        with BundleContext(bundle_path) as bundle_ctx:
            if do_css:
                report = css_service.apply(
                    bundle_ctx, candidate_assets=candidate_assets)
            else:
                bundle_ctx.load()
                report = PatchReport(bundle_ctx.bundle_path,
                                     dry_run=self.options.dry_run)

            if texture_service:
                if bundle_index is None:
                    bundle_index = load_cached_bundle_index(
                        self.css_dir,
                        bundle_path,
                        skin_cache_dir=skin_cache_dir,
                    )
                texture_names = gather_texture_names_from_index(bundle_index)
                if should_swap_textures(
                    bundle_name=bundle_path.name,
                    texture_names=texture_names,
                    target_names=target_names_from_map,
                    replace_stems=replace_stems,
                    want_icons=want_icons,
                    want_backgrounds=want_bgs,
                ):
                    try:
                        texture_service.apply(
                            bundle_ctx,
                            self.css_dir,
                            self.out_dir,
                            report,
                        )
                    except Exception as exc:
                        log.warning(
                            f"[WARN] Texture swap skipped due to error: {exc}")
                else:
                    log.debug(
                        "[TEXTURE] Prefilter: skipping bundle with no matching names.")

            saved_path = bundle_ctx.save_modified(
                self.out_dir, dry_run=self.options.dry_run
            )
            if saved_path:
                report.mark_saved(saved_path)

        return report


def run_patch(
    css_dir: Path,
    out_dir: Path,
    bundle: Optional[Path] = None,
    patch_direct: bool = False,
    debug_export: bool = False,
    backup: bool = False,
    dry_run: bool = False,
    use_scan_cache: bool = True,
    refresh_scan_cache: bool = False,
) -> PipelineResult:
    """High-level entry to patch bundles based on CSS in css_dir."""

    options = PipelineOptions(
        patch_direct=patch_direct,
        debug_export=debug_export,
        backup=backup,
        dry_run=dry_run,
        use_scan_cache=use_scan_cache,
        refresh_scan_cache=refresh_scan_cache,
    )
    pipeline = SkinPatchPipeline(css_dir, out_dir, options)
    return pipeline.run(bundle=bundle)
