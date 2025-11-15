from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple, Any, Set
from types import SimpleNamespace
import gc
import json
import os
import shutil
import sys
import UnityPy

try:
    from UnityPy.classes.math import ColorRGBA as UnityColorRGBA
except Exception:  # pragma: no cover - UnityPy may not expose ColorRGBA in tests
    UnityColorRGBA = None

from .logger import get_logger
from .cache import load_or_cache_config, cache_dir
from .context import BundleContext, PatchReport
from .services import (
    CssPatchOptions,
    CssPatchService,
    TextureSwapOptions,
    TextureSwapService,
)
from .font_swap_service import (
    FontSwapOptions,
    FontSwapService,
)
from .css_utils import (
    build_selector_from_parts,
    clean_for_json,
    hex_to_rgba,
    serialize_stylesheet_to_uss,
    normalize_css_color,
)
from .value_parsers import (
    parse_float_value,
    parse_keyword_value,
    parse_resource_value,
    parse_variable_value,
)
from .property_handlers import (
    PROPERTY_TYPE_MAP,
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
from .css_sources import CollectedCss, collect_css_from_dir, load_targeting_hints
from .bundle_paths import infer_bundle_files

log = get_logger(__name__)
# -----------------------------
# Core patcher
# -----------------------------


def _build_unity_color(
    colors: Iterable[Any], r: float, g: float, b: float, a: float
) -> Any:
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


def _infer_property_type_from_name(prop_name: str) -> Optional[int]:
    """
    Infer the Unity StyleSheet value type from the property name.

    Returns the expected Unity type (1=keyword, 2=float, 4=color, 7=resource, 8=enum)
    or None if the type cannot be inferred from the name.

    This helps handle cases where a variable's value may be ambiguous but the
    naming convention indicates the intended type.
    """
    prop_lower = prop_name.lower()

    # Padding/margin/spacing properties should be floats
    if any(
        keyword in prop_lower
        for keyword in ["padding", "margin", "spacing", "gap", "offset"]
    ):
        return 2  # Float

    # Border radius properties should be floats
    if "radius" in prop_lower:
        return 2  # Float

    # Size/dimension properties should be floats
    if any(
        keyword in prop_lower
        for keyword in ["width", "height", "size", "thickness", "weight"]
    ):
        return 2  # Float

    # Color-related properties should be colors
    if any(
        keyword in prop_lower
        for keyword in [
            "color",
            "colour",
            "background",
            "foreground",
            "border-color",
            "tint",
        ]
    ):
        # Exception: border-width, border-radius, etc. are not colors
        if not any(
            keyword in prop_lower for keyword in ["width", "radius", "thickness"]
        ):
            return 4  # Color

    # Font properties should be resources
    if "font" in prop_lower and "size" not in prop_lower:
        return 7  # Resource

    # Direction/alignment properties should be keywords
    if any(
        keyword in prop_lower
        for keyword in ["direction", "align", "justify", "display", "position"]
    ):
        return 1  # Keyword/Enum

    return None


def _is_color_property(prop_name: str, value: Any) -> bool:
    """Check if a property should be treated as a color."""
    # If the value is a CSS variable reference (starts with -- or var()), it's not a literal color
    if isinstance(value, str):
        value_stripped = value.strip()
        if value_stripped.startswith("--") or value_stripped.startswith("var("):
            return False

        # Check if it's a color value (hex string)
        if normalize_css_color(value_stripped) is not None:
            return True

    # Otherwise check if the property name suggests it's a color
    inferred_type = _infer_property_type_from_name(prop_name)
    if inferred_type is not None:
        return inferred_type == 4

    return False


def _patch_float_property(
    data: Any,
    prop: Any,
    prop_name: str,
    value_str: str,
    name: str,
) -> Tuple[bool, Optional[int]]:
    """
    Patch a float property value.

    For shorthand properties (border-radius, padding, margin), a single value
    will be expanded to all related values (e.g., all 4 corners for border-radius).

    For CSS variable definitions (--var-name), removes variable references so the
    literal float value is shown in USS export.

    Returns (changed, patched_index) tuple.
    """
    parsed = parse_float_value(value_str)
    if parsed is None:
        return False, None

    float_value = parsed.unity_value
    floats = getattr(data, "floats", [])
    if not hasattr(data, "floats"):
        setattr(data, "floats", floats)

    values = list(getattr(prop, "m_Values", []))
    is_css_variable = prop_name.startswith("--")

    # Check if this is a shorthand property that should expand to multiple values
    is_shorthand = prop_name in {"border-radius", "padding", "margin", "border-width"}

    # Get all existing Type 2 (float) values
    float_values = [
        (val, getattr(val, "valueIndex", None))
        for val in values
        if getattr(val, "m_ValueType", None) == 2
    ]

    # Get all variable references (Type 3 or 10) that should be removed for shorthand
    var_references = [
        val
        for val in values
        if getattr(val, "m_ValueType", None) in {3, 10}
    ] if is_shorthand else []

    if is_shorthand and (len(float_values) > 1 or var_references):
        # Shorthand property with multiple values - update all of them
        changed = False
        first_index = None

        # Update existing float values
        for val, value_index in float_values:
            if value_index is not None and 0 <= value_index < len(floats):
                old_value = floats[value_index]
                if abs(old_value - float_value) >= 1e-6:  # Value differs
                    floats[value_index] = float_value
                    log.info(
                        f"  [PATCHED - float shorthand] {name}: {prop_name} (index {value_index}): {old_value} → {float_value}"
                    )
                    changed = True
                if first_index is None:
                    first_index = value_index

        # Remove ALL variable references and string references from the values list
        # When user provides explicit numeric value, only keep float values
        values_list = getattr(prop, "m_Values", [])
        removed_any = False
        strings = getattr(data, "strings", [])
        # Filter out Type 3/8/10 values (variable references and strings)
        remaining_values = []
        for val in values_list:
            val_type = getattr(val, "m_ValueType", None)
            val_index = getattr(val, "valueIndex", None)

            # Check if this is a variable reference
            is_var_ref = False
            if val_type in {3, 10}:  # Variable reference types
                is_var_ref = True
            elif val_type == 8 and val_index is not None and 0 <= val_index < len(strings):
                # Type 8 string that might be a variable name
                string_val = strings[val_index]
                if string_val and string_val.startswith('--'):
                    is_var_ref = True

            if is_var_ref:
                log.info(
                    f"  [PATCHED - remove var ref] {name}: {prop_name} removed type {val_type} index {val_index}"
                )
                removed_any = True
            else:
                remaining_values.append(val)

        # Replace the entire list by setting the attribute
        if removed_any:
            setattr(prop, "m_Values", remaining_values)
            changed = True

        return changed, first_index
    elif float_values:
        # Single value property or shorthand with only one value - update the first one
        val, value_index = float_values[0]
        if value_index is not None and 0 <= value_index < len(floats):
            old_value = floats[value_index]
            changed = False
            if abs(old_value - float_value) >= 1e-6:  # Value differs
                floats[value_index] = float_value
                log.info(
                    f"  [PATCHED - float] {name}: {prop_name} (index {value_index}): {old_value} → {float_value}"
                )
                changed = True

            # For CSS variable definitions, remove ALL variable references and string references
            # so the literal float value is shown in USS export
            if is_css_variable:
                values_list = getattr(prop, "m_Values", [])
                remaining_values = []
                removed_any = False
                strings = getattr(data, "strings", [])

                for val in values_list:
                    val_type = getattr(val, "m_ValueType", None)
                    val_index = getattr(val, "valueIndex", None)

                    # Check if this is a variable reference
                    is_var_ref = False
                    if val_type in {3, 10}:  # Variable reference types
                        is_var_ref = True
                    elif val_type == 8 and val_index is not None and 0 <= val_index < len(strings):
                        # Type 8 string that might be a variable name
                        string_val = strings[val_index]
                        if string_val and string_val.startswith('--'):
                            is_var_ref = True

                    if is_var_ref:
                        log.info(
                            f"  [PATCHED - remove var ref] {name}: {prop_name} removed type {val_type} index {val_index}"
                        )
                        removed_any = True
                    else:
                        remaining_values.append(val)

                if removed_any:
                    setattr(prop, "m_Values", remaining_values)
                    changed = True

            return changed, value_index if changed else None

    # No existing float value, create new one
    floats.append(float_value)
    new_index = len(floats) - 1

    # Update or create value handle
    handle = next(
        (val for val in values if getattr(val, "m_ValueType", None) in {2, 3, 8, 10}),
        values[0] if values else None,
    )
    if handle:
        setattr(handle, "m_ValueType", 2)
        setattr(handle, "valueIndex", new_index)
        log.info(
            f"  [PATCHED - float] {name}: {prop_name} (new index {new_index}) → {float_value}"
        )
        return True, new_index

    return False, None


def _patch_keyword_property(
    data: Any,
    prop: Any,
    prop_name: str,
    value_str: str,
    name: str,
) -> Tuple[bool, Optional[int]]:
    """
    Patch a keyword/enum property value.

    Returns (changed, patched_index) tuple.
    """
    parsed = parse_keyword_value(value_str)
    if parsed is None:
        return False, None

    keyword = parsed.keyword
    strings = getattr(data, "strings", [])
    if not hasattr(data, "strings"):
        setattr(data, "strings", strings)

    values = list(getattr(prop, "m_Values", []))

    # Try to find existing Type 1 or 8 (keyword/enum) value
    for val in values:
        value_type = getattr(val, "m_ValueType", None)
        if value_type in {1, 8}:
            value_index = getattr(val, "valueIndex", None)
            if value_index is not None and 0 <= value_index < len(strings):
                old_value = strings[value_index]
                if old_value == keyword:  # No change
                    return False, value_index
                strings[value_index] = keyword
                log.info(
                    f"  [PATCHED - keyword] {name}: {prop_name} (index {value_index}): {old_value} → {keyword}"
                )
                return True, value_index

    # No existing keyword value, create new one
    strings.append(keyword)
    new_index = len(strings) - 1

    # Update or create value handle
    handle = next(
        (val for val in values if getattr(val, "m_ValueType", None) in {1, 3, 8, 10}),
        values[0] if values else None,
    )
    if handle:
        # Use Type 8 (enum) by default for keywords
        setattr(handle, "m_ValueType", 8)
        setattr(handle, "valueIndex", new_index)
        log.info(
            f"  [PATCHED - keyword] {name}: {prop_name} (new index {new_index}) → {keyword}"
        )
        return True, new_index

    return False, None


def _patch_resource_property(
    data: Any,
    prop: Any,
    prop_name: str,
    value_str: str,
    name: str,
) -> Tuple[bool, Optional[int]]:
    """
    Patch a resource reference property value.

    Unity USS Type 7 (AssetReference) uses string paths in the strings array,
    not binary PPtr<Object> references. Unity resolves "resource://..." paths
    at runtime when building the UI. This means:
    - We store string paths like "resource://fonts/MyFont"
    - Unity's resource loader finds and loads the actual Font asset
    - No FileID/PathID needed for USS stylesheets
    - This is different from MonoBehaviour serialization which uses PPtr

    Returns (changed, patched_index) tuple.
    """
    parsed = parse_resource_value(value_str)
    if parsed is None:
        return False, None

    resource_path = parsed.unity_path
    strings = getattr(data, "strings", [])
    if not hasattr(data, "strings"):
        setattr(data, "strings", strings)

    values = list(getattr(prop, "m_Values", []))

    # Try to find existing Type 7 (resource) value
    for val in values:
        if getattr(val, "m_ValueType", None) == 7:
            value_index = getattr(val, "valueIndex", None)
            if value_index is not None and 0 <= value_index < len(strings):
                old_value = strings[value_index]
                if old_value == resource_path:  # No change
                    return False, value_index
                # Update in-place, preserving the array index
                strings[value_index] = resource_path
                log.info(
                    f"  [PATCHED - resource] {name}: {prop_name} (index {value_index}): {old_value} → {resource_path}"
                )
                return True, value_index

    # No existing resource value, create new one
    strings.append(resource_path)
    new_index = len(strings) - 1

    # Update or create value handle
    handle = next(
        (val for val in values if getattr(val, "m_ValueType", None) in {3, 7, 8, 10}),
        values[0] if values else None,
    )
    if handle:
        setattr(handle, "m_ValueType", 7)
        setattr(handle, "valueIndex", new_index)
        log.info(
            f"  [PATCHED - resource] {name}: {prop_name} (new index {new_index}) → {resource_path}"
        )
        return True, new_index

    return False, None


class CssPatcher:
    def __init__(
        self,
        css_data: CollectedCss,
        patch_direct: bool = False,
        debug_export_dir: Optional[Path] = None,
        dry_run: bool = False,
        selectors_filter: Optional[Set[str]] = None,
        selector_props_filter: Optional[Set[Tuple[str, str]]] = None,
        primary_variable_stylesheet: Optional[str] = None,
        primary_selector_stylesheet: Optional[str] = None,
    ) -> None:
        self.css_data = css_data
        self.patch_direct = patch_direct
        self.debug_export_dir = debug_export_dir
        self.dry_run = dry_run
        # Optional targeting hints (advanced)
        # If provided, limit selector/property override application to these filters.
        # selectors_filter contains selector strings (with or without leading '.')
        # selector_props_filter contains (selector, property) tuples (selector can be with or without '.')
        self.selectors_filter = selectors_filter
        self.selector_props_filter = selector_props_filter
        # Primary stylesheets for new content (Phase 3)
        # If set, new variables go to primary_variable_stylesheet (default: FigmaStyleVariables)
        # If set, new selectors go to primary_selector_stylesheet (default: FigmaGeneratedStyles)
        self.primary_variable_stylesheet = (
            primary_variable_stylesheet.lower()
            if primary_variable_stylesheet
            else "figmastylevariables"
        )
        self.primary_selector_stylesheet = (
            primary_selector_stylesheet.lower()
            if primary_selector_stylesheet
            else "figmageneratedstyles"
        )

    def patch_bundle_file(
        self,
        bundle_path: Path,
        out_dir: Path,
        candidate_assets: Optional[Set[str]] = None,
    ) -> Optional[List[str]]:
        bundle_context = BundleContext(bundle_path, loader=UnityPy.load)
        try:
            report = self.patch_bundle(
                bundle_context, candidate_assets=candidate_assets
            )
            if not report.has_changes:
                return report.summary_lines if self.dry_run else None
            if self.dry_run:
                return report.summary_lines

            saved_path = bundle_context.save_modified(out_dir, dry_run=self.dry_run)
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

    def _build_global_selector_registry(
        self, stylesheets: List[Tuple[Any, str]]
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Build global registry of selectors and variables across all stylesheets.

        Returns:
            (selector_registry, variable_registry) where:
            - selector_registry: {".green": ["figmastylevariables", "othersheet"], ...}
            - variable_registry: {"--primary-color": ["figmastylevariables"], ...}

        Note: Stylesheet names are stored in lowercase for case-insensitive comparison.
        """
        from collections import defaultdict

        selector_registry: DefaultDict[str, List[str]] = defaultdict(list)
        variable_registry: DefaultDict[str, List[str]] = defaultdict(list)

        for data, name in stylesheets:
            # Normalize name to lowercase for case-insensitive comparison
            name_lower = name.lower()

            # Extract all selectors from complex selectors
            complex_selectors = getattr(data, "m_ComplexSelectors", [])
            for sel in complex_selectors:
                if hasattr(sel, "m_Selectors") and sel.m_Selectors:
                    for s in sel.m_Selectors:
                        parts = getattr(s, "m_Parts", [])
                        if parts:
                            selector_text = build_selector_from_parts(parts)
                            if (
                                selector_text
                                and name_lower not in selector_registry[selector_text]
                            ):
                                selector_registry[selector_text].append(name_lower)

            # Extract all variables from rules
            rules = getattr(data, "m_Rules", [])
            for rule in rules:
                for prop in getattr(rule, "m_Properties", []):
                    prop_name = getattr(prop, "m_Name", "")
                    if prop_name.startswith("--"):
                        if name_lower not in variable_registry[prop_name]:
                            variable_registry[prop_name].append(name_lower)

        return dict(selector_registry), dict(variable_registry)

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

        original_uss: List[
            Tuple[Any, Any, str, Dict[str, str], Dict[Tuple[str, str], str], bool]
        ] = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            data = obj.read()
            if not hasattr(data, "colors") or not hasattr(data, "strings"):
                continue
            name = getattr(data, "m_Name", "UnnamedStyleSheet")
            if candidate_assets is not None and name not in candidate_assets:
                continue
            css_vars_for_asset, selector_overrides_for_asset, has_targeted_sources = (
                self._effective_overrides(name)
            )
            will_patch = self._will_patch(
                data,
                css_vars_for_asset,
                selector_overrides_for_asset,
            )
            if self.debug_export_dir and will_patch and not self.dry_run:
                self.debug_export_dir.mkdir(parents=True, exist_ok=True)
                self._export_debug_original(name, data)
            original_uss.append(
                (
                    obj,
                    data,
                    name,
                    css_vars_for_asset,
                    selector_overrides_for_asset,
                    has_targeted_sources,
                )
            )

        # Build global registry of selectors and variables across all stylesheets
        # This enables smart update mode (Option 3) to prevent cross-file duplicates
        stylesheet_data = [(data, name) for (_, data, name, _, _, _) in original_uss]
        self._global_selector_registry, self._global_variable_registry = (
            self._build_global_selector_registry(stylesheet_data)
        )

        if self._global_selector_registry or self._global_variable_registry:
            log.info(
                f"  [GLOBAL REGISTRY] Found {len(self._global_selector_registry)} selectors "
                f"and {len(self._global_variable_registry)} variables across {len(stylesheet_data)} stylesheets"
            )

        for (
            obj,
            data,
            name,
            css_vars_for_asset,
            selector_overrides_for_asset,
            has_targeted_sources,
        ) in original_uss:
            found_styles += 1
            pv, pd, changed = self._apply_patches_to_stylesheet(
                name,
                data,
                css_vars_for_asset,
                selector_overrides_for_asset,
                has_targeted_sources,
            )
            patched_vars += pv
            patched_direct += pd
            if changed:
                any_changes = True
                changed_asset_names.add(name)
                if not self.dry_run:
                    data.save()

        if not any_changes:
            log.info("No changes detected; skipping bundle write and debug outputs.")
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

    def _effective_overrides(
        self,
        stylesheet_name: str,
    ) -> Tuple[Dict[str, str], Dict[Tuple[str, str], str], bool]:
        """Get effective CSS overrides for a stylesheet.

        Returns:
            (vars_combined, selectors_combined, has_targeted_sources)
            - vars_combined: Variables for this stylesheet (targeted if mapped, else global)
            - selectors_combined: Selectors for this stylesheet (targeted if mapped, else global)
            - has_targeted_sources: True if this stylesheet has explicit targeting (asset_map or files_by_stem)

        Behavior:
            - Stylesheets with explicit targeting get ONLY their targeted content
            - Stylesheets without explicit targeting get global content (from unmapped CSS files)
        """
        vars_combined: Dict[str, str] = {}
        selectors_combined: Dict[Tuple[str, str], str] = {}

        key = stylesheet_name.lower()
        seen_sources: Set[int] = set()
        has_targeted_sources = False

        # Check for explicit targeting in asset_map
        if key in self.css_data.asset_map:
            has_targeted_sources = True
            for overrides in self.css_data.asset_map[key]:
                seen_sources.add(id(overrides))
                vars_combined.update(overrides.vars)
                selectors_combined.update(overrides.selectors)

        # Check for explicit targeting in files_by_stem
        if key in self.css_data.files_by_stem:
            for overrides in self.css_data.files_by_stem[key]:
                ident = id(overrides)
                if ident in seen_sources:
                    continue
                has_targeted_sources = True
                vars_combined.update(overrides.vars)
                selectors_combined.update(overrides.selectors)

        # Only add global content if NOT explicitly targeted
        # This ensures mapped stylesheets only get their specific content
        if not has_targeted_sources:
            vars_combined.update(self.css_data.global_vars)
            selectors_combined.update(self.css_data.global_selectors)

        return vars_combined, selectors_combined, has_targeted_sources

    def _will_patch(
        self,
        data,
        css_vars: Dict[str, str],
        selector_overrides: Dict[Tuple[str, str], str],
    ) -> bool:
        # Check var-based direct property patches
        for rule in getattr(data, "m_Rules", []):
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                # Be permissive: try raw, stripped, and prefixed forms so
                # bundle property names that differ by leading dashes still match
                prop_candidates = []
                if prop_name is not None:
                    prop_candidates = [
                        prop_name,
                        prop_name.lstrip("-"),
                        "--" + prop_name.lstrip("-"),
                    ]
                match_key = next((k for k in prop_candidates if k in css_vars), None)
                if match_key:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(
                                getattr(data, "colors", [])
                            ):
                                hex_val = css_vars[match_key]
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
                candidates = [
                    prop_name,
                    prop_name.lstrip("-"),
                    "--" + prop_name.lstrip("-"),
                ]
                match_key = next((k for k in candidates if k in css_vars), None)
                if not match_key:
                    continue
                has_literal_color = any(
                    getattr(val, "m_ValueType", None) == 4
                    for val in getattr(prop, "m_Values", [])
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
            if var_name not in css_vars:
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
                target = css_vars.get(var_name)
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
                if cand in css_vars:
                    found_val = css_vars[cand]
                    break
            if not found_val:
                continue
            try:
                tr, tg, tb, ta = hex_to_rgba(found_val)
            except ValueError:
                return False  # Skip invalid hex colors
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
                            if value_index is not None and 0 <= value_index < len(
                                getattr(data, "colors", [])
                            ):
                                prop_name = getattr(prop, "m_Name", "")
                                css_match = next(
                                    (
                                        css_vars[k]
                                        for k in css_vars
                                        if k.endswith(prop_name)
                                    ),
                                    None,
                                )
                                if css_match:
                                    r, g, b, a = hex_to_rgba(css_match)
                                    col = data.colors[value_index]
                                    if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                        return True

        # Selector/property overrides
        selectors = (
            getattr(data, "m_ComplexSelectors", [])
            if hasattr(data, "m_ComplexSelectors")
            else []
        )
        rules = getattr(data, "m_Rules", [])
        for rule_idx, rule in enumerate(rules):
            selector_texts: List[str] = []
            for sel in selectors:
                if (
                    hasattr(sel, "ruleIndex")
                    and getattr(sel, "ruleIndex", -1) == rule_idx
                ):
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
                            (sv, prop_name) in self.selector_props_filter
                            for sv in sel_variants
                        )
                        if not allowed:
                            continue
                    elif self.selectors_filter is not None:
                        # Require selector to be in allowed set
                        allowed = any(
                            sv in self.selectors_filter for sv in sel_variants
                        )
                        if not allowed:
                            continue

                    if (selector_text, prop_name) in selector_overrides or (
                        selector_text.lstrip("."),
                        prop_name,
                    ) in selector_overrides:
                        for val in getattr(prop, "m_Values", []):
                            if getattr(val, "m_ValueType", None) == 4:
                                value_index = getattr(val, "valueIndex", None)
                                if value_index is not None and 0 <= value_index < len(
                                    getattr(data, "colors", [])
                                ):
                                    return True
        return False

    def _split_rule_for_selector(
        self,
        data,
        rule_idx: int,
        target_selector_text: str,
        name: str,
    ) -> int:
        """
        Split a shared rule so a single selector can be patched independently.

        If multiple selectors share a rule, this creates a new rule with copies
        of all properties and moves just the target selector to the new rule.

        Args:
            data: Unity stylesheet data object
            rule_idx: Index of the rule to potentially split
            target_selector_text: The selector we want to isolate (e.g., ".calendar-day-current")
            name: Stylesheet name for logging

        Returns:
            The rule index to use for patching (either the new rule or the original if no split needed)
        """

        selectors = getattr(data, "m_ComplexSelectors", [])
        rules = getattr(data, "m_Rules", [])

        if not selectors or rule_idx >= len(rules):
            return rule_idx

        # Find all selectors pointing to this rule
        selectors_in_rule = []
        for sel_idx, sel in enumerate(selectors):
            if getattr(sel, "ruleIndex", -1) == rule_idx:
                # Get the selector text
                for selector in getattr(sel, "m_Selectors", []):
                    parts = getattr(selector, "m_Parts", [])
                    sel_text = build_selector_from_parts(parts)
                    if sel_text == target_selector_text or sel_text.lstrip(".") == target_selector_text:
                        selectors_in_rule.append((sel_idx, sel_text))
                        break

        # If only one selector uses this rule, no split needed
        if len(selectors_in_rule) <= 1:
            # Check if there are other selectors with different names in this rule
            other_selectors = []
            for sel_idx, sel in enumerate(selectors):
                if getattr(sel, "ruleIndex", -1) == rule_idx:
                    for selector in getattr(sel, "m_Selectors", []):
                        parts = getattr(selector, "m_Parts", [])
                        sel_text = build_selector_from_parts(parts)
                        if sel_text != target_selector_text and sel_text.lstrip(".") != target_selector_text:
                            other_selectors.append((sel_idx, sel_text))
                            break

            if not other_selectors:
                return rule_idx  # Only our selector uses this rule

        # Multiple selectors share this rule - need to split
        log.info(
            f"  [RULE SPLIT] {name}: Splitting rule {rule_idx} to isolate {target_selector_text}"
        )

        # Create a new rule by manually copying properties (can't use deepcopy on Unity objects)
        original_rule = rules[rule_idx]

        # Create a new rule object of the same type
        new_rule = type(original_rule)()

        # Create NEW property objects (not just copy the list)
        # This ensures modifications to the new rule don't affect the old rule
        original_props = getattr(original_rule, "m_Properties", [])
        if original_props:
            new_props = []
            for orig_prop in original_props:
                # Create a new property object of the same type
                new_prop = type(orig_prop)()
                # Copy the property name
                setattr(new_prop, "m_Name", getattr(orig_prop, "m_Name", ""))
                # Copy line number if present
                if hasattr(orig_prop, "m_Line"):
                    setattr(new_prop, "m_Line", getattr(orig_prop, "m_Line"))
                # Create NEW value objects too (not just a new list)
                # This ensures when patching modifies a value object, it doesn't affect the original rule
                orig_values = getattr(orig_prop, "m_Values", [])
                new_values = []
                for orig_val in orig_values:
                    new_val = type(orig_val)()
                    # Copy all attributes
                    setattr(new_val, "m_ValueType", getattr(orig_val, "m_ValueType", None))
                    setattr(new_val, "valueIndex", getattr(orig_val, "valueIndex", None))
                    new_values.append(new_val)
                setattr(new_prop, "m_Values", new_values)
                new_props.append(new_prop)
            setattr(new_rule, "m_Properties", new_props)

        # Copy line number if it exists
        if hasattr(original_rule, "line"):
            setattr(new_rule, "line", getattr(original_rule, "line"))

        # Add the new rule to the rules array
        rules.append(new_rule)
        new_rule_idx = len(rules) - 1

        # Move only the target selector(s) to the new rule
        for sel_idx, sel_text in selectors_in_rule:
            setattr(selectors[sel_idx], "ruleIndex", new_rule_idx)
            log.info(
                f"  [RULE SPLIT] {name}: Moved {sel_text} from rule {rule_idx} to new rule {new_rule_idx}"
            )

        return new_rule_idx

    def _apply_patches_to_stylesheet(
        self,
        name: str,
        data,
        css_vars: Dict[str, str],
        selector_overrides: Dict[Tuple[str, str], str],
        has_targeted_sources: bool = False,
    ) -> Tuple[int, int, bool]:
        """Apply CSS patches to a stylesheet.

        Args:
            name: Stylesheet name (e.g., "FMColours", "inlineStyle")
            data: Unity stylesheet data object
            css_vars: CSS variables to patch
            selector_overrides: Selector overrides to patch
            has_targeted_sources: True if this stylesheet has explicit CSS targeting (not just global)

        Returns:
            (patched_vars, patched_direct, changed) tuple
        """
        patched_vars = 0
        patched_direct = 0
        changed = False

        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        rules = getattr(data, "m_Rules", [])
        selectors = (
            getattr(data, "m_ComplexSelectors", [])
            if hasattr(data, "m_ComplexSelectors")
            else []
        )

        # Track which CSS variables have been matched/patched
        matched_css_vars: Set[str] = set()
        # Track which selector+property pairs have been matched/patched
        matched_selectors: Set[Tuple[str, str]] = set()

        # Direct property patches (by var name == prop m_Name)
        direct_property_patched_indices = set()
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                # Normalize prop name variants to be permissive when matching keys
                match_key = None
                if prop_name is not None:
                    candidates = [
                        prop_name,
                        prop_name.lstrip("-"),
                        "--" + prop_name.lstrip("-"),
                    ]
                    match_key = next((k for k in candidates if k in css_vars), None)
                if match_key:
                    value_str = css_vars[match_key]
                    matched_css_vars.add(match_key)  # Track matched variable

                    # Check if it's a color property (backwards compatibility)
                    if _is_color_property(prop_name, value_str):
                        for val in getattr(prop, "m_Values", []):
                            if getattr(val, "m_ValueType", None) == 4:
                                value_index = getattr(val, "valueIndex", None)
                                if value_index is not None and 0 <= value_index < len(
                                    colors
                                ):
                                    hex_val = value_str
                                    r, g, b, a = hex_to_rgba(hex_val)
                                    col = colors[value_index]
                                    if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                        col.r, col.g, col.b, col.a = r, g, b, a
                                        patched_vars += 1
                                        direct_property_patched_indices.add(value_index)
                                        log.info(
                                            f"  [PATCHED - direct property] {name}: {match_key} (color index {value_index}) → {hex_val}"
                                        )
                                        changed = True
                    else:
                        # Try to patch as non-color property (float, keyword, resource)
                        prop_type = PROPERTY_TYPE_MAP.get(prop_name)

                        # For CSS custom properties (--variables), infer the type if not in map
                        if not prop_type and prop_name.startswith("--"):
                            inferred_type = _infer_property_type_from_name(prop_name)
                            if inferred_type == 2:  # Float
                                prop_changed, index = _patch_float_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    patched_vars += 1
                                    changed = True
                            elif inferred_type == 1 or inferred_type == 8:  # Keyword
                                prop_changed, index = _patch_keyword_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    patched_vars += 1
                                    changed = True
                            elif inferred_type == 7:  # Resource
                                prop_changed, index = _patch_resource_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    patched_vars += 1
                                    changed = True
                        elif prop_type:
                            # Determine which type to use based on property definition
                            # patched = False
                            if 2 in prop_type.unity_types:  # Float
                                prop_changed, index = _patch_float_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    # patched = True
                                    patched_vars += 1
                                    changed = True
                            elif 7 in prop_type.unity_types:  # Resource
                                prop_changed, index = _patch_resource_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    # patched = True
                                    patched_vars += 1
                                    changed = True
                            elif (
                                1 in prop_type.unity_types or 8 in prop_type.unity_types
                            ):  # Keyword
                                prop_changed, index = _patch_keyword_property(
                                    data, prop, prop_name, value_str, name
                                )
                                if prop_changed:
                                    # patched = True
                                    patched_vars += 1
                                    changed = True

        # If a root-level variable only references other tokens (e.g. var(--foo)) and the user
        # supplies a color override, convert that definition into a literal color so the new
        # value survives in the bundle even without updating the referenced token.
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if prop_name is None:
                    continue
                candidates = [
                    prop_name,
                    prop_name.lstrip("-"),
                    "--" + prop_name.lstrip("-"),
                ]
                match_key = next((k for k in candidates if k in css_vars), None)
                if not match_key:
                    continue

                value_str = css_vars[match_key]
                matched_css_vars.add(match_key)  # Track matched variable

                values = list(getattr(prop, "m_Values", []))
                if not values:
                    continue

                # Check if it's a color property
                if _is_color_property(prop_name, value_str):
                    has_literal_color = any(
                        getattr(val, "m_ValueType", None) == 4 for val in values
                    )
                    if has_literal_color:
                        continue

                    # Convert variable reference to literal color
                    hex_val = value_str
                    r, g, b, a = hex_to_rgba(hex_val)
                    new_color = _build_unity_color(colors, r, g, b, a)
                    colors.append(new_color)
                    new_index = len(colors) - 1

                    handle = next(
                        (
                            val
                            for val in values
                            if getattr(val, "m_ValueType", None) in {3, 8, 10}
                        ),
                        values[0],
                    )
                    setattr(handle, "m_ValueType", 4)
                    setattr(handle, "valueIndex", new_index)

                    patched_vars += 1
                    direct_property_patched_indices.add(new_index)
                    changed = True
                    log.info(
                        f"  [PATCHED - var literal color] {name}: {match_key} (new color index {new_index}) → {hex_val}"
                    )
                else:
                    # Handle non-color properties (float, keyword, resource)
                    prop_type = PROPERTY_TYPE_MAP.get(prop_name)
                    if not prop_type:
                        continue

                    # Check what type of literal value we need
                    if 2 in prop_type.unity_types:  # Float
                        # Check if property already has a literal float (Type 2)
                        has_literal_float = any(
                            getattr(val, "m_ValueType", None) == 2 for val in values
                        )
                        if has_literal_float:
                            continue

                        # Convert variable reference to literal float
                        parsed = parse_float_value(value_str)
                        if parsed:
                            floats = getattr(data, "floats", [])
                            if not hasattr(data, "floats"):
                                setattr(data, "floats", floats)

                            floats.append(parsed.unity_value)
                            new_index = len(floats) - 1

                            handle = next(
                                (
                                    val
                                    for val in values
                                    if getattr(val, "m_ValueType", None)
                                    in {2, 3, 8, 10}
                                ),
                                values[0],
                            )
                            setattr(handle, "m_ValueType", 2)
                            setattr(handle, "valueIndex", new_index)

                            patched_vars += 1
                            changed = True
                            log.info(
                                f"  [PATCHED - var literal float] {name}: {match_key} (new float index {new_index}) → {parsed.unity_value}"
                            )

                    elif (
                        1 in prop_type.unity_types or 8 in prop_type.unity_types
                    ):  # Keyword
                        # Check if property already has a literal keyword (Type 1/8)
                        has_literal_keyword = any(
                            getattr(val, "m_ValueType", None) in {1, 8}
                            for val in values
                        )
                        if has_literal_keyword:
                            continue

                        # Convert variable reference to literal keyword
                        parsed = parse_keyword_value(value_str)
                        if parsed:
                            strings = getattr(data, "strings", [])
                            if not hasattr(data, "strings"):
                                setattr(data, "strings", strings)

                            strings.append(parsed.keyword)
                            new_index = len(strings) - 1

                            handle = next(
                                (
                                    val
                                    for val in values
                                    if getattr(val, "m_ValueType", None)
                                    in {1, 3, 8, 10}
                                ),
                                values[0],
                            )
                            setattr(
                                handle, "m_ValueType", 8
                            )  # Use Type 8 (enum) for keywords
                            setattr(handle, "valueIndex", new_index)

                            patched_vars += 1
                            changed = True
                            log.info(
                                f"  [PATCHED - var literal keyword] {name}: {match_key} (new string index {new_index}) → {parsed.keyword}"
                            )

                    elif 7 in prop_type.unity_types:  # Resource
                        # Check if property already has a literal resource (Type 7)
                        has_literal_resource = any(
                            getattr(val, "m_ValueType", None) == 7 for val in values
                        )
                        if has_literal_resource:
                            continue

                        # Convert variable reference to literal resource path
                        parsed = parse_resource_value(value_str)
                        if parsed:
                            strings = getattr(data, "strings", [])
                            if not hasattr(data, "strings"):
                                setattr(data, "strings", strings)

                            strings.append(parsed.unity_path)
                            new_index = len(strings) - 1

                            handle = next(
                                (
                                    val
                                    for val in values
                                    if getattr(val, "m_ValueType", None)
                                    in {3, 7, 8, 10}
                                ),
                                values[0],
                            )
                            setattr(handle, "m_ValueType", 7)
                            setattr(handle, "valueIndex", new_index)

                            patched_vars += 1
                            changed = True
                            log.info(
                                f"  [PATCHED - var literal resource] {name}: {match_key} (new string index {new_index}) → {parsed.unity_path}"
                            )

        # Strict CSS variable patching
        color_indices_to_patch: Dict[int, str] = {}
        for color_idx in range(len(colors)):
            if color_idx in direct_property_patched_indices:
                continue
            if color_idx >= len(strings):
                continue
            var_name = strings[color_idx]
            if var_name not in css_vars:
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
                    f"  [WILL PATCH] {name}: {var_name} (color index {color_idx}) → {css_vars[var_name]}"
                )

        for color_idx, var_name in color_indices_to_patch.items():
            hex_val = css_vars.get(var_name)
            if not hex_val:
                continue
            r, g, b, a = hex_to_rgba(hex_val)
            col = colors[color_idx]
            if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                col.r, col.g, col.b, col.a = r, g, b, a
                patched_vars += 1
                log.info(
                    f"  [PATCHED] {name}: {var_name} (color index {color_idx}) → {hex_val}"
                )
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
                                (
                                    css_vars[k]
                                    for k in css_vars
                                    if k.endswith(prop_name)
                                ),
                                None,
                            )
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

        # Pre-process selector overrides: split rules where multiple selectors share a rule
        # This prevents unintended propagation when patching one selector affects others
        rules_to_split = {}  # Maps (selector_text, rule_idx) -> needs split
        for rule_idx, rule in enumerate(rules):
            selector_texts: List[str] = []
            for sel in selectors:
                if (
                    hasattr(sel, "ruleIndex")
                    and getattr(sel, "ruleIndex", -1) == rule_idx
                ):
                    for selector in getattr(sel, "m_Selectors", []):
                        parts = getattr(selector, "m_Parts", [])
                        selector_texts.append(build_selector_from_parts(parts))

            # Check if any selector in this rule has overrides
            for selector_text in selector_texts:
                for prop in getattr(rule, "m_Properties", []):
                    prop_name = getattr(prop, "m_Name", None)
                    keys_to_try = [
                        (selector_text, prop_name),
                        (selector_text.lstrip("."), prop_name),
                    ]
                    for key in keys_to_try:
                        if key in selector_overrides:
                            # This selector has an override - mark for potential split
                            rules_to_split[(selector_text, rule_idx)] = True

        # Now actually split the rules
        rule_index_mapping = {}  # Maps old rule_idx -> new rule_idx for selectors that got split
        for (selector_text, old_rule_idx) in rules_to_split:
            new_rule_idx = self._split_rule_for_selector(
                data, old_rule_idx, selector_text, name
            )
            if new_rule_idx != old_rule_idx:
                # Rule was split
                rule_index_mapping[(selector_text, old_rule_idx)] = new_rule_idx
                changed = True

        # Selector/property overrides
        for rule_idx, rule in enumerate(rules):
            selector_texts: List[str] = []
            for sel in selectors:
                if (
                    hasattr(sel, "ruleIndex")
                    and getattr(sel, "ruleIndex", -1) == rule_idx
                ):
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
                            if (
                                sel_only not in self.selectors_filter
                                and sel_only.lstrip(".") not in self.selectors_filter
                            ):
                                continue
                        if key in selector_overrides:
                            value_str = selector_overrides[key]
                            matched_selectors.add(
                                key
                            )  # Track matched selector+property
                            log.info(
                                f"  [DEBUG] Selector/property match: {key} in {name}, patching to {value_str}"
                            )

                            # Check if it's a variable reference first
                            parsed_var = parse_variable_value(value_str)
                            # Also check for bare CSS variable names (starting with --)
                            is_bare_variable = isinstance(value_str, str) and value_str.strip().startswith("--")

                            if parsed_var is not None or is_bare_variable:
                                # Variable reference (var(--name)) or bare variable name (--name)
                                if parsed_var is not None:
                                    var_name = parsed_var.unity_variable_name
                                else:
                                    # It's a bare variable name - normalize it
                                    var_name = value_str.strip()
                                    if not var_name.startswith("--"):
                                        var_name = f"--{var_name}"

                                values = list(getattr(prop, "m_Values", []))

                                # Find or add the variable name to strings array
                                if var_name not in strings:
                                    strings.append(var_name)
                                var_index = strings.index(var_name)

                                # Update the first value to Type 10 (variable reference)
                                if values:
                                    val = values[0]
                                    old_type = getattr(val, "m_ValueType", None)
                                    old_index = getattr(val, "valueIndex", None)

                                    setattr(val, "m_ValueType", 10)
                                    setattr(val, "valueIndex", var_index)

                                    patched_vars += 1
                                    changed = True
                                    log.info(
                                        f"  [PATCHED - selector/property variable] {name}: {key} → {value_str} (was type {old_type} index {old_index})"
                                    )

                                    try:
                                        touches = getattr(
                                            self, "_selector_touches", None
                                        )
                                        if touches is not None:
                                            norm_sel = key[0]
                                            touches.setdefault(
                                                (
                                                    (
                                                        norm_sel
                                                        if norm_sel.startswith(".")
                                                        else norm_sel
                                                    ),
                                                    prop_name,
                                                ),
                                                set(),
                                            ).add(name)
                                    except Exception:
                                        pass
                                else:
                                    log.warning(
                                        f"  [WARN] No values found for {key} in {name}, cannot patch to variable"
                                    )
                            # Check if it's a color property
                            elif _is_color_property(prop_name, value_str):
                                # Handle color property for selector overrides
                                # IMPORTANT: For selector properties, we ALWAYS create a new color
                                # entry instead of modifying existing ones. This prevents unintended
                                # global propagation to other selectors that may share the same color index.
                                values = list(getattr(prop, "m_Values", []))
                                r, g, b, a = hex_to_rgba(value_str)

                                # Find existing Type 4 value to replace
                                replacement_handle = next(
                                    (
                                        val
                                        for val in values
                                        if getattr(val, "m_ValueType", None) == 4
                                    ),
                                    None,
                                )

                                # If no Type 4 value, try to find Type 3/8/10 to convert
                                if not replacement_handle:
                                    replacement_handle = next(
                                        (
                                            val
                                            for val in values
                                            if getattr(val, "m_ValueType", None)
                                            in {3, 8, 10}
                                        ),
                                        None,
                                    )

                                if replacement_handle is None:
                                    log.warning(
                                        f"  [WARN] No suitable value found to convert for {key} in {name}."
                                    )
                                    continue

                                # Create a new color entry for this selector property
                                # This ensures we don't affect other selectors that may share the same color index
                                new_color = _build_unity_color(colors, r, g, b, a)
                                colors.append(new_color)
                                new_index = len(colors) - 1

                                # Update the value to point to the new color
                                old_index = getattr(replacement_handle, "valueIndex", None)
                                setattr(replacement_handle, "m_ValueType", 4)
                                setattr(replacement_handle, "valueIndex", new_index)

                                patched_vars += 1
                                direct_property_patched_indices.add(new_index)
                                changed = True
                                log.info(
                                    f"  [PATCHED - selector/property] {name}: {key} (new color index {new_index}, was {old_index}) → {value_str}"
                                )

                                try:
                                    touches = getattr(
                                        self, "_selector_touches", None
                                    )
                                    if touches is not None:
                                        norm_sel = key[0]
                                        touches.setdefault(
                                            (
                                                (
                                                    norm_sel
                                                    if norm_sel.startswith(".")
                                                    else norm_sel
                                                ),
                                                prop_name,
                                            ),
                                            set(),
                                        ).add(name)
                                except Exception:
                                    log.exception(
                                        "Exception occurred while updating selector touches for %s",
                                        key,
                                    )
                            else:
                                # Try to patch as non-color property (float, keyword, resource)
                                prop_type = PROPERTY_TYPE_MAP.get(prop_name)
                                if prop_type:
                                    prop_changed = False
                                    if 2 in prop_type.unity_types:  # Float
                                        prop_changed, _ = _patch_float_property(
                                            data, prop, prop_name, value_str, name
                                        )
                                    elif 7 in prop_type.unity_types:  # Resource
                                        prop_changed, _ = _patch_resource_property(
                                            data, prop, prop_name, value_str, name
                                        )
                                    elif (
                                        1 in prop_type.unity_types
                                        or 8 in prop_type.unity_types
                                    ):  # Keyword
                                        prop_changed, _ = _patch_keyword_property(
                                            data, prop, prop_name, value_str, name
                                        )

                                    if prop_changed:
                                        patched_vars += 1
                                        changed = True
                                        try:
                                            touches = getattr(
                                                self, "_selector_touches", None
                                            )
                                            if touches is not None:
                                                norm_sel = key[0]
                                                touches.setdefault(
                                                    (
                                                        (
                                                            norm_sel
                                                            if norm_sel.startswith(".")
                                                            else norm_sel
                                                        ),
                                                        prop_name,
                                                    ),
                                                    set(),
                                                ).add(name)
                                        except Exception:
                                            pass

        # Phase 3.1: Smart new variable placement
        # First, check which variables already exist to avoid duplicates
        existing_var_names = set()
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", "")
                if prop_name.startswith("--"):
                    existing_var_names.add(prop_name)

        # Calculate unmatched variables (not matched AND not already in stylesheet)
        unmatched_vars = set(css_vars.keys()) - matched_css_vars - existing_var_names

        if unmatched_vars:
            # Option 3: Smart Update Mode with Global Registry
            # Check if variables exist in other stylesheets (global registry)
            registry = getattr(self, "_global_variable_registry", {})
            name_lower = name.lower()
            vars_in_other_files = {
                var: registry[var]
                for var in unmatched_vars
                if var in registry and name_lower not in registry[var]
            }

            # Filter out variables that exist elsewhere (they'll be updated there)
            truly_new_vars = unmatched_vars - set(vars_in_other_files.keys())

            if truly_new_vars:
                # Smart placement: Only add new variables if:
                # 1. This stylesheet has explicit targeting (has_targeted_sources), OR
                # 2. This stylesheet is the primary variable stylesheet
                should_add_vars = has_targeted_sources or (
                    name_lower == self.primary_variable_stylesheet
                )

                if should_add_vars:
                    reason = (
                        "explicit targeting"
                        if has_targeted_sources
                        else "primary variable stylesheet"
                    )
                    log.info(
                        f"  [PHASE 3.1] Adding {len(truly_new_vars)} new CSS variables to {name} ({reason})"
                    )
                    new_vars_created = self._add_new_css_variables(
                        data, truly_new_vars, css_vars, name
                    )
                    if new_vars_created > 0:
                        patched_vars += new_vars_created
                        changed = True
                        log.info(
                            f"  [ADDED] {new_vars_created} new CSS variables to {name}"
                        )
                else:
                    # Skip adding new variables to this stylesheet
                    log.info(
                        f"  [PHASE 3.1] Skipping {len(truly_new_vars)} new variables for {name} "
                        f"(not targeted, primary is '{self.primary_variable_stylesheet}')"
                    )
                    if len(truly_new_vars) <= 5:
                        log.info(f"    Variables: {', '.join(sorted(truly_new_vars))}")
                    else:
                        log.info(
                            f"    Variables: {', '.join(sorted(list(truly_new_vars)[:5]))}... (and {len(truly_new_vars) - 5} more)"
                        )

            # Log variables that exist in other files (smart update)
            if vars_in_other_files:
                for var, locations in sorted(vars_in_other_files.items()):
                    log.info(
                        f"  [PHASE 3.1] Skipping {var} for {name} "
                        f"(already exists in {', '.join(locations)}, will update there)"
                    )

        # Phase 3.2: Smart new selector placement
        # Calculate unmatched selectors (similar to unmatched_vars calculation)
        unmatched_selectors = set(selector_overrides.keys()) - matched_selectors

        # First, check which selectors already exist to avoid duplicates
        existing_selector_texts = set()
        complex_selectors = getattr(data, "m_ComplexSelectors", [])
        for sel in complex_selectors:
            # Build selector text from parts
            if hasattr(sel, "m_Selectors") and sel.m_Selectors:
                for s in sel.m_Selectors:
                    parts = getattr(s, "m_Parts", [])
                    if parts:
                        selector_text = build_selector_from_parts(parts)
                        existing_selector_texts.add(selector_text)

        # Only add truly new selectors (not matched AND not already in stylesheet)
        truly_new_selectors = {
            (sel, prop)
            for (sel, prop) in unmatched_selectors
            if sel not in existing_selector_texts
        }

        # Remove duplicate selector entries (e.g., both ".test-class" and "test-class")
        # Keep only the version WITH the dot for class selectors
        deduplicated_selectors = set()
        selectors_with_dots = {
            (sel, prop) for (sel, prop) in truly_new_selectors if sel.startswith(".")
        }
        selectors_without_dots = {
            (sel, prop)
            for (sel, prop) in truly_new_selectors
            if not sel.startswith(".")
        }

        for sel, prop in selectors_with_dots:
            deduplicated_selectors.add((sel, prop))

        for sel, prop in selectors_without_dots:
            # Only add if there's no .version already
            dot_version = f".{sel}"
            if (dot_version, prop) not in selectors_with_dots:
                deduplicated_selectors.add((sel, prop))

        truly_new_selectors = deduplicated_selectors

        if truly_new_selectors:
            # Option 3: Smart Update Mode with Global Registry
            # Check if selectors exist in other stylesheets (global registry)
            registry = getattr(self, "_global_selector_registry", {})
            name_lower = name.lower()
            selectors_in_other_files = {}
            filtered_new_selectors = set()

            for sel, prop in truly_new_selectors:
                if sel in registry and name_lower not in registry[sel]:
                    # Selector exists in other file(s), will be updated there
                    selectors_in_other_files[sel] = registry[sel]
                else:
                    # Truly new selector (doesn't exist anywhere)
                    filtered_new_selectors.add((sel, prop))

            if filtered_new_selectors:
                # Smart placement: Only add new selectors if:
                # 1. This stylesheet has explicit targeting (has_targeted_sources), OR
                # 2. This stylesheet is the primary selector stylesheet
                should_add_selectors = has_targeted_sources or (
                    name_lower == self.primary_selector_stylesheet
                )

                if should_add_selectors:
                    reason = (
                        "explicit targeting"
                        if has_targeted_sources
                        else "primary selector stylesheet"
                    )
                    log.info(
                        f"  [PHASE 3.2] Adding {len(filtered_new_selectors)} new selector properties to {name} ({reason})"
                    )
                    new_props_created = self._add_new_css_selectors(
                        data, filtered_new_selectors, selector_overrides, name
                    )
                    if new_props_created > 0:
                        patched_vars += new_props_created
                        changed = True
                        log.info(
                            f"  [ADDED] {new_props_created} new selector properties to {name}"
                        )
                else:
                    # Skip adding new selectors to this stylesheet
                    selector_list = sorted(
                        set(sel for sel, prop in filtered_new_selectors)
                    )
                    log.info(
                        f"  [PHASE 3.2] Skipping {len(filtered_new_selectors)} new selector properties for {name} "
                        f"(not targeted, primary is '{self.primary_selector_stylesheet}')"
                    )
                    if len(selector_list) <= 5:
                        log.info(f"    Selectors: {', '.join(selector_list)}")
                    else:
                        log.info(
                            f"    Selectors: {', '.join(selector_list[:5])}... (and {len(selector_list) - 5} more)"
                        )

            # Log selectors that exist in other files (smart update)
            if selectors_in_other_files:
                for sel, locations in sorted(selectors_in_other_files.items()):
                    log.info(
                        f"  [PHASE 3.2] Skipping {sel} for {name} "
                        f"(already exists in {', '.join(locations)}, will update there)"
                    )

        if self.debug_export_dir and changed and not self.dry_run:
            # Ensure dir exists before exporting
            self.debug_export_dir.mkdir(parents=True, exist_ok=True)
            self._export_debug_patched(name, data)

        return patched_vars, patched_direct, changed

    def _add_new_css_variables(
        self,
        data: Any,
        unmatched_vars: Set[str],
        css_vars: Dict[str, Any],
        stylesheet_name: str,
    ) -> int:
        """
        Add new CSS variables that don't exist in the stylesheet.

        Creates properties in a root-level rule for variables that weren't
        matched during normal patching. This allows users to add completely
        new CSS variables.

        Args:
            data: Unity StyleSheet data object
            unmatched_vars: Set of CSS variable names that weren't matched
            css_vars: Dictionary mapping variable names to values
            stylesheet_name: Name of the stylesheet for logging

        Returns:
            Number of new variables created
        """
        if not unmatched_vars:
            return 0

        # Get arrays
        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        floats = getattr(data, "floats", [])
        rules = getattr(data, "m_Rules", [])

        if not hasattr(data, "floats"):
            setattr(data, "floats", floats)

        # Find the rule that already contains CSS variables
        # CSS variables are properties starting with "--"
        root_rule = None
        # selectors = getattr(data, "m_ComplexSelectors", [])

        if rules:
            # Look for a rule that already has CSS variables (properties starting with --)
            # This is the safest approach - only add to a rule that's clearly for variables
            for i, rule in enumerate(rules):
                props = getattr(rule, "m_Properties", [])
                has_variables = any(
                    getattr(prop, "m_Name", "").startswith("--") for prop in props
                )
                if has_variables:
                    root_rule = rule
                    log.debug(
                        f"  [DEBUG] Found existing variables rule at index {i} in {stylesheet_name}"
                    )
                    break

        # If no rule with variables exists, create a NEW one
        # DON'T insert at index 0 - this shifts all indices and can break selectors
        # Instead, append at the end
        if root_rule is None:
            # Copy structure from existing rule if possible
            if rules:
                import copy

                template_rule = rules[0]
                root_rule = copy.copy(template_rule)
                # Clear properties but keep structure
                setattr(root_rule, "m_Properties", [])
                # Set line to -1 to indicate synthetic rule
                if hasattr(root_rule, "line"):
                    setattr(root_rule, "line", -1)
                if hasattr(root_rule, "m_Line"):
                    setattr(root_rule, "m_Line", -1)
            else:
                # Fallback: create minimal structure with all required fields
                root_rule = SimpleNamespace()
                setattr(root_rule, "m_Properties", [])
                setattr(root_rule, "line", -1)
                setattr(root_rule, "m_Line", -1)
                setattr(root_rule, "m_Column", 0)

            # Append at the end to avoid shifting indices
            rules.append(root_rule)
            new_rule_index = len(rules) - 1

            log.info(
                f"  [CREATED] New variables rule at index {new_rule_index} in {stylesheet_name}"
            )

        properties = getattr(root_rule, "m_Properties", [])
        if not isinstance(properties, list):
            properties = []
            setattr(root_rule, "m_Properties", properties)

        # Calculate the next m_Line value for new properties
        # Find the highest m_Line in existing properties
        next_line = None
        if properties:
            max_line = max(
                (getattr(p, "m_Line", None) for p in properties),
                key=lambda x: x if x is not None else -1,
                default=None
            )
            if max_line is not None and max_line >= 0:
                next_line = max_line + 1

        created_count = 0
        for var_name in sorted(unmatched_vars):  # Sort for consistent ordering
            value_str = css_vars[var_name]

            # Determine value type and create property
            # Copy structure from existing property if possible
            if properties:
                import copy

                prop = copy.copy(properties[0])
                setattr(prop, "m_Name", var_name)
                setattr(prop, "m_Values", [])
                # Set the next sequential m_Line value
                if next_line is not None:
                    setattr(prop, "m_Line", next_line)
                    next_line += 1  # Increment for next property
            else:
                # Create minimal property object with required Unity fields
                prop = SimpleNamespace()
                setattr(prop, "m_Name", var_name)
                setattr(prop, "m_Values", [])
                setattr(prop, "m_Line", -1)
                setattr(prop, "m_Column", 0)

            values_list = getattr(prop, "m_Values")

            # CSS variable DEFINITIONS should NOT have Type 10 reference
            # Type 10 is only for REFERENCES like var(--name), not definitions
            # Variable definitions just have the actual value (Type 4 for color, Type 2 for float, etc.)

            # Create value object
            # Try to copy structure from existing value if available
            existing_values = []
            for existing_prop in properties:
                existing_vals = getattr(existing_prop, "m_Values", [])
                if existing_vals:
                    existing_values.extend(existing_vals)
                    break

            if existing_values:
                import copy

                value_obj = copy.copy(existing_values[0])
                # Will set m_ValueType and valueIndex below
            else:
                # Create minimal value object with required Unity fields
                value_obj = SimpleNamespace()
                setattr(value_obj, "m_Line", -1)
                setattr(value_obj, "m_Column", 0)

            # Detect value type and add to appropriate array
            # First try to infer type from property name for better type detection
            inferred_type = _infer_property_type_from_name(var_name)

            # Check if it's a variable reference (var(--name))
            parsed_var = parse_variable_value(value_str)
            if parsed_var is not None:
                # Variable reference - store as Type 10
                var_ref_name = parsed_var.unity_variable_name
                strings.append(var_ref_name)
                value_index = len(strings) - 1

                setattr(value_obj, "m_ValueType", 10)
                setattr(value_obj, "valueIndex", value_index)
                log.info(
                    f"  [NEW VAR - reference] {stylesheet_name}: {var_name} → {value_str} (string index {value_index})"
                )

            elif inferred_type == 2:
                # Inferred as float from name (e.g., padding, radius)
                parsed_float = parse_float_value(value_str)
                if parsed_float is not None:
                    floats.append(parsed_float.unity_value)
                    value_index = len(floats) - 1

                    setattr(value_obj, "m_ValueType", 2)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW VAR - float (inferred)] {stylesheet_name}: {var_name} → {parsed_float.unity_value} (float index {value_index})"
                    )
                else:
                    # Couldn't parse as float, fall back to string
                    strings.append(value_str)
                    value_index = len(strings) - 1
                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.warning(
                        f"  [NEW VAR - string (fallback)] {stylesheet_name}: {var_name} → {value_str}"
                    )

            elif inferred_type == 4 or _is_color_property(var_name, value_str):
                # Inferred as color from name or value
                normalized_color = normalize_css_color(value_str)
                if normalized_color:
                    r, g, b, a = hex_to_rgba(normalized_color)
                    new_color = _build_unity_color(colors, r, g, b, a)
                    colors.append(new_color)
                    value_index = len(colors) - 1

                    setattr(value_obj, "m_ValueType", 4)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW VAR - color] {stylesheet_name}: {var_name} → {value_str} (color index {value_index})"
                    )
                else:
                    # Couldn't parse as color, fall back to string
                    strings.append(value_str)
                    value_index = len(strings) - 1
                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.warning(
                        f"  [NEW VAR - string (fallback)] {stylesheet_name}: {var_name} → {value_str}"
                    )

            elif inferred_type == 1 or inferred_type == 8:
                # Inferred as keyword from name
                parsed_keyword = parse_keyword_value(value_str)
                if parsed_keyword is not None:
                    strings.append(parsed_keyword.keyword)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW VAR - keyword (inferred)] {stylesheet_name}: {var_name} → {parsed_keyword.keyword} (string index {value_index})"
                    )
                else:
                    # Couldn't parse as keyword, fall back to string
                    strings.append(value_str)
                    value_index = len(strings) - 1
                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.warning(
                        f"  [NEW VAR - string (fallback)] {stylesheet_name}: {var_name} → {value_str}"
                    )

            elif inferred_type == 7:
                # Inferred as resource from name
                parsed_resource = parse_resource_value(value_str)
                if parsed_resource is not None:
                    strings.append(parsed_resource.unity_path)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 7)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW VAR - resource (inferred)] {stylesheet_name}: {var_name} → {parsed_resource.unity_path} (string index {value_index})"
                    )
                else:
                    # Couldn't parse as resource, fall back to string
                    strings.append(value_str)
                    value_index = len(strings) - 1
                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.warning(
                        f"  [NEW VAR - string (fallback)] {stylesheet_name}: {var_name} → {value_str}"
                    )

            elif (parsed_float := parse_float_value(value_str)) is not None:
                # No type inferred, but value parses as float
                floats.append(parsed_float.unity_value)
                value_index = len(floats) - 1

                setattr(value_obj, "m_ValueType", 2)
                setattr(value_obj, "valueIndex", value_index)
                log.info(
                    f"  [NEW VAR - float] {stylesheet_name}: {var_name} → {parsed_float.unity_value} (float index {value_index})"
                )

            elif (parsed_keyword := parse_keyword_value(value_str)) is not None:
                # Value parses as keyword
                strings.append(parsed_keyword.keyword)
                value_index = len(strings) - 1

                setattr(value_obj, "m_ValueType", 8)
                setattr(value_obj, "valueIndex", value_index)
                log.info(
                    f"  [NEW VAR - keyword] {stylesheet_name}: {var_name} → {parsed_keyword.keyword} (string index {value_index})"
                )

            elif (parsed_resource := parse_resource_value(value_str)) is not None:
                # Value parses as resource
                strings.append(parsed_resource.unity_path)
                value_index = len(strings) - 1

                setattr(value_obj, "m_ValueType", 7)
                setattr(value_obj, "valueIndex", value_index)
                log.info(
                    f"  [NEW VAR - resource] {stylesheet_name}: {var_name} → {parsed_resource.unity_path} (string index {value_index})"
                )

            else:
                # Fallback: store as string (Type 8)
                strings.append(value_str)
                value_index = len(strings) - 1

                setattr(value_obj, "m_ValueType", 8)
                setattr(value_obj, "valueIndex", value_index)
                log.warning(
                    f"  [NEW VAR - unknown] {stylesheet_name}: {var_name} → {value_str} (stored as string)"
                )

            values_list.append(value_obj)
            properties.append(prop)
            created_count += 1

        return created_count

    def _add_new_css_selectors(
        self,
        data: Any,
        unmatched_selectors: Set[Tuple[str, str]],
        selector_overrides: Dict[Tuple[str, str], Any],
        stylesheet_name: str,
    ) -> int:
        """
        Add new CSS selectors that don't exist in the stylesheet.

        Creates new rules and complex selectors for selector+property pairs that
        weren't matched during normal patching. This allows users to add completely
        new CSS classes or selectors.

        Args:
            data: Unity StyleSheet data object
            unmatched_selectors: Set of (selector, property) tuples that weren't matched
            selector_overrides: Dictionary mapping (selector, property) to values
            stylesheet_name: Name of the stylesheet for logging

        Returns:
            Number of new properties created across all selectors
        """
        if not unmatched_selectors:
            return 0

        # Get arrays
        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        floats = getattr(data, "floats", [])
        rules = getattr(data, "m_Rules", [])
        complex_selectors = getattr(data, "m_ComplexSelectors", [])

        if not hasattr(data, "floats"):
            setattr(data, "floats", floats)
        if not hasattr(data, "m_ComplexSelectors"):
            setattr(data, "m_ComplexSelectors", complex_selectors)

        # Group properties by selector
        from collections import defaultdict

        selector_props: DefaultDict[str, List[Tuple[str, Any]]] = defaultdict(list)
        for selector, prop_name in unmatched_selectors:
            value = selector_overrides.get((selector, prop_name))
            if value is not None:
                selector_props[selector].append((prop_name, value))

        created_count = 0
        for selector_text in sorted(selector_props.keys()):
            props_to_add = selector_props[selector_text]

            # Create new rule (copy from existing if possible)
            if rules:
                import copy

                new_rule = copy.copy(rules[0])
                setattr(new_rule, "m_Properties", [])
                if hasattr(new_rule, "line"):
                    setattr(new_rule, "line", -1)
                if hasattr(new_rule, "m_Line"):
                    setattr(new_rule, "m_Line", -1)
            else:
                new_rule = SimpleNamespace()
                setattr(new_rule, "m_Properties", [])
                setattr(new_rule, "line", -1)
                setattr(new_rule, "m_Line", -1)
                setattr(new_rule, "m_Column", 0)
            rule_index = len(rules)
            rules.append(new_rule)

            # Add all properties to the rule
            properties = getattr(new_rule, "m_Properties")
            for prop_name, value_str in props_to_add:
                # Create property (copy from existing if possible)
                existing_prop = None
                for rule in rules:
                    for p in getattr(rule, "m_Properties", []):
                        if getattr(p, "m_Name", None):
                            existing_prop = p
                            break
                    if existing_prop:
                        break

                if existing_prop:
                    import copy

                    prop = copy.copy(existing_prop)
                    setattr(prop, "m_Name", prop_name)
                    setattr(prop, "m_Values", [])
                else:
                    # Create minimal property object with required Unity fields
                    prop = SimpleNamespace()
                    setattr(prop, "m_Name", prop_name)
                    setattr(prop, "m_Values", [])
                    setattr(prop, "m_Line", -1)
                    setattr(prop, "m_Column", 0)

                values_list = getattr(prop, "m_Values")

                # Create value object (copy from existing if possible)
                existing_value = None
                if existing_prop:
                    existing_vals = getattr(existing_prop, "m_Values", [])
                    if existing_vals:
                        existing_value = existing_vals[0]

                if existing_value:
                    import copy

                    value_obj = copy.copy(existing_value)
                else:
                    # Create minimal value object with required Unity fields
                    value_obj = SimpleNamespace()
                    setattr(value_obj, "m_Line", -1)
                    setattr(value_obj, "m_Column", 0)

                # Detect value type and add to appropriate array
                # Check for variable reference first (before color check)
                if (parsed_var := parse_variable_value(value_str)) is not None:
                    # Variable reference (var(--name))
                    # Store the variable name in strings array and create Type 10 reference
                    var_name = parsed_var.unity_variable_name
                    strings.append(var_name)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 10)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW SELECTOR - variable] {stylesheet_name}: {selector_text} {{ {prop_name}: {value_str}; }}"
                    )

                elif _is_color_property(prop_name, value_str):
                    # Color value
                    r, g, b, a = hex_to_rgba(value_str)
                    new_color = _build_unity_color(colors, r, g, b, a)
                    colors.append(new_color)
                    value_index = len(colors) - 1

                    setattr(value_obj, "m_ValueType", 4)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW SELECTOR - color] {stylesheet_name}: {selector_text} {{ {prop_name}: {value_str}; }}"
                    )

                elif (parsed_float := parse_float_value(value_str)) is not None:
                    # Float value
                    floats.append(parsed_float.unity_value)
                    value_index = len(floats) - 1

                    setattr(value_obj, "m_ValueType", 2)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW SELECTOR - float] {stylesheet_name}: {selector_text} {{ {prop_name}: {parsed_float.unity_value}; }}"
                    )

                elif (parsed_keyword := parse_keyword_value(value_str)) is not None:
                    # Keyword value
                    strings.append(parsed_keyword.keyword)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW SELECTOR - keyword] {stylesheet_name}: {selector_text} {{ {prop_name}: {parsed_keyword.keyword}; }}"
                    )

                elif (parsed_resource := parse_resource_value(value_str)) is not None:
                    # Resource value
                    strings.append(parsed_resource.unity_path)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 7)
                    setattr(value_obj, "valueIndex", value_index)
                    log.info(
                        f"  [NEW SELECTOR - resource] {stylesheet_name}: {selector_text} {{ {prop_name}: {parsed_resource.unity_path}; }}"
                    )

                else:
                    # Fallback: store as string
                    strings.append(value_str)
                    value_index = len(strings) - 1

                    setattr(value_obj, "m_ValueType", 8)
                    setattr(value_obj, "valueIndex", value_index)
                    log.warning(
                        f"  [NEW SELECTOR - unknown] {stylesheet_name}: {selector_text} {{ {prop_name}: {value_str}; }}"
                    )

                values_list.append(value_obj)
                properties.append(prop)
                created_count += 1

            # Create ComplexSelector for this rule
            complex_selector = self._create_complex_selector(
                selector_text, rule_index, strings
            )
            complex_selectors.append(complex_selector)

            log.info(
                f"  [NEW SELECTOR] {stylesheet_name}: Created selector '{selector_text}' with {len(props_to_add)} properties"
            )

        return created_count

    def _create_complex_selector(
        self, selector_text: str, rule_index: int, strings: List[str]
    ) -> SimpleNamespace:
        """
        Create a ComplexSelector from a selector string (e.g., ".button", "#myid", "Label").

        Args:
            selector_text: CSS selector string
            rule_index: Index of the rule this selector points to
            strings: Strings array (for storing selector values)

        Returns:
            ComplexSelector object
        """
        complex_selector = SimpleNamespace()
        setattr(complex_selector, "ruleIndex", rule_index)
        setattr(complex_selector, "m_Selectors", [])

        # Calculate specificity based on selector type
        # Unity USS specificity: ID=100, Class=10, Element=1, Universal=0
        specificity = 0
        if selector_text.startswith("#"):
            specificity = 100  # ID selector
        elif selector_text.startswith("."):
            specificity = 10  # Class selector
        elif selector_text.startswith(":"):
            specificity = 10  # Pseudo-class selector (same as class)
        elif selector_text == "*":
            specificity = 0  # Universal selector
        else:
            specificity = 1  # Element selector

        setattr(complex_selector, "m_Specificity", specificity)

        # Create a simple selector with parts
        simple_selector = SimpleNamespace()
        setattr(simple_selector, "m_Parts", [])
        setattr(simple_selector, "m_PreviousRelationship", 0)  # No relationship

        # Parse selector text into parts
        parts = getattr(simple_selector, "m_Parts")
        selector_part = self._parse_selector_to_part(selector_text, strings)
        parts.append(selector_part)

        selectors_list = getattr(complex_selector, "m_Selectors")
        selectors_list.append(simple_selector)

        return complex_selector

    def _parse_selector_to_part(
        self, selector_text: str, strings: List[str]
    ) -> SimpleNamespace:
        """
        Parse a selector string into a Unity selector part.

        Args:
            selector_text: CSS selector string (e.g., ".button", "#myid", "Label", ":hover")
            strings: Strings array (for storing values)

        Returns:
            Selector part object with m_Value and m_Type
        """
        part = SimpleNamespace()

        # Add required fields that Unity expects
        setattr(part, "m_Line", -1)
        setattr(part, "m_Column", 0)

        # Determine selector type and value
        if selector_text.startswith("#"):
            # ID selector
            value = selector_text[1:]  # Remove #
            setattr(part, "m_Type", 2)
            setattr(part, "m_Value", value)
        elif selector_text.startswith("."):
            # Class selector
            value = selector_text[1:]  # Remove .
            setattr(part, "m_Type", 3)
            setattr(part, "m_Value", value)
        elif selector_text.startswith(":"):
            # Pseudo-class selector
            value = selector_text[1:]  # Remove :
            setattr(part, "m_Type", 4)
            setattr(part, "m_Value", value)
        else:
            # Element/type selector
            setattr(part, "m_Type", 1)
            setattr(part, "m_Value", selector_text)

        return part

    def _export_debug_original(self, name: str, data) -> None:
        assert self.debug_export_dir is not None
        uss_text = serialize_stylesheet_to_uss(data)
        (self.debug_export_dir / f"original_{name}.uss").write_text(
            uss_text, encoding="utf-8"
        )

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
                    if k in {
                        "m_CorrespondingSourceObject",
                        "m_PrefabAsset",
                        "m_PrefabInstance",
                        "m_GameObject",
                    }:
                        out_json[k] = {"m_FileID": 0, "m_PathID": 0}
                    elif k == "m_EditorClassIdentifier":
                        out_json[k] = ""
                    elif k in {"m_EditorHideFlags", "m_HideFlags"}:
                        out_json[k] = 0
            structure = {k: raw_json[k] for k in raw_json if k not in root_fields}
            if (
                "m_ImportedWithWarnings" in structure
                and structure["m_ImportedWithWarnings"] is None
            ):
                structure["m_ImportedWithWarnings"] = 0
            out_json["m_Structure"] = structure
            (self.debug_export_dir / f"original_{name}.json").write_text(
                json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            log.warning(f"[WARN] Could not export original JSON for {name}: {e}")

        minimal = {
            "m_Name": getattr(data, "m_Name", None),
            "strings": list(getattr(data, "strings", [])),
            "colors": [
                {"r": c.r, "g": c.g, "b": c.b, "a": c.a}
                for c in getattr(data, "colors", [])
            ],
        }
        (self.debug_export_dir / f"original_{name}_minimal.json").write_text(
            json.dumps(minimal, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _export_debug_patched(self, name: str, data) -> None:
        assert self.debug_export_dir is not None
        uss_text = serialize_stylesheet_to_uss(data)
        (self.debug_export_dir / f"patched_{name}.uss").write_text(
            uss_text, encoding="utf-8"
        )
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
                    if k in {
                        "m_CorrespondingSourceObject",
                        "m_PrefabAsset",
                        "m_PrefabInstance",
                        "m_GameObject",
                    }:
                        out_json[k] = {"m_FileID": 0, "m_PathID": 0}
                    elif k == "m_EditorClassIdentifier":
                        out_json[k] = ""
                    elif k in {"m_EditorHideFlags", "m_HideFlags"}:
                        out_json[k] = 0
            structure = {k: raw_json[k] for k in raw_json if k not in root_fields}
            if (
                "m_ImportedWithWarnings" in structure
                and structure["m_ImportedWithWarnings"] is None
            ):
                structure["m_ImportedWithWarnings"] = 0
            out_json["m_Structure"] = structure
            (self.debug_export_dir / f"patched_{name}.json").write_text(
                json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            log.warning(f"[WARN] Could not export patched JSON for {name}: {e}")
        minimal = {
            "m_Name": getattr(data, "m_Name", None),
            "strings": list(getattr(data, "strings", [])),
            "colors": [
                {"r": c.r, "g": c.g, "b": c.b, "a": c.a}
                for c in getattr(data, "colors", [])
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
    """Result object returned by the skin patching pipeline.

    Attributes:
        bundle_reports: List of individual bundle patch reports with details per bundle.
        css_bundles_modified: Number of CSS bundles that were actually modified.
        texture_replacements_total: Total count of texture replacements across all bundles.
        texture_bundles_written: Number of bundles written with texture changes.
        font_replacements_total: Total count of font replacements across all bundles.
        font_bundles_written: Number of bundles written with font changes.
        bundles_requested: Total number of bundles requested for processing.
        summary_lines: Human-readable summary lines for CLI output.
    """

    bundle_reports: List[PatchReport]
    css_bundles_modified: int
    texture_replacements_total: int
    texture_bundles_written: int
    font_replacements_total: int
    font_bundles_written: int
    bundles_requested: int
    summary_lines: List[str] = field(default_factory=list)

    @classmethod
    def empty(cls) -> "PipelineResult":
        return cls(
            bundle_reports=[],
            css_bundles_modified=0,
            texture_replacements_total=0,
            texture_bundles_written=0,
            font_replacements_total=0,
            font_bundles_written=0,
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
        css_data = collect_css_from_dir(self.css_dir)
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
        debug_dir = (self.out_dir / "debug_uss") if self.options.debug_export else None
        css_service = CssPatchService(
            css_data,
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
                bundle_files = [p for p in bundle.iterdir() if p.suffix == ".bundle"]
            else:
                bundle_files = [bundle]
        else:
            bundle_files = infer_bundle_files(self.css_dir)
            if not bundle_files:
                log.error(
                    "No bundle specified and none could be inferred from config. Provide --bundle."
                )
                return PipelineResult.empty()

        bundle_files = self._sorted_bundle_files(bundle_files)

        bundles_requested = len(bundle_files)

        skin_is_known = (self.css_dir / "config.json").exists()
        cache_candidates: Dict[Path, Optional[Set[str]]] = {}
        skin_cache_dir: Optional[Path] = None
        if self.options.use_scan_cache and skin_is_known:
            try:
                skin_cache_dir = (
                    cache_dir(root=self.css_dir.parent.parent) / self.css_dir.name
                )
                skin_cache_dir.mkdir(parents=True, exist_ok=True)
                for b in bundle_files:
                    cand = _load_or_refresh_scan_cache(
                        skin_cache_dir,
                        self.css_dir,
                        b,
                        refresh=self.options.refresh_scan_cache,
                        css_data=css_data,
                        patch_direct=self.options.patch_direct,
                    )
                    cache_candidates[b] = cand
            except Exception as e:
                log.debug(f"Scan cache unavailable: {e}")
                skin_cache_dir = None

        includes = getattr(cfg_model, "includes", None)
        includes_list: List[str] = list(includes) if isinstance(includes, list) else []
        want_icons = any(x.strip().lower() == "assets/icons" for x in includes_list)
        want_bgs = any(x.strip().lower() == "assets/backgrounds" for x in includes_list)
        icon_dir = self.css_dir / "assets" / "icons"
        bg_dir = self.css_dir / "assets" / "backgrounds"
        replace_stems = set(
            collect_replacement_stems(icon_dir) + collect_replacement_stems(bg_dir)
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
                TextureSwapOptions(includes=includes_list, dry_run=self.options.dry_run)
            )

        # Font swap service
        font_targets_present = any(
            x.strip().lower() in {"fonts", "assets/fonts", "all"} for x in includes_list
        )
        font_service: Optional[FontSwapService] = None
        if font_targets_present:
            font_service = FontSwapService(
                FontSwapOptions(
                    includes=includes_list,
                    dry_run=self.options.dry_run,
                    auto_convert=True,  # Auto-convert to match original format (critical!)
                    strict_format=False,  # Allow conversion to handle mismatches
                )
            )

        summary_lines: List[str] = []
        bundle_reports: List[PatchReport] = []
        css_bundles_modified = 0
        texture_replacements_total = 0
        texture_bundles_written = 0
        font_replacements_total = 0
        font_bundles_written = 0

        log.info(f"\n📦 Processing {len(bundle_files)} bundle(s)...")

        for bundle_index, bundle_path in enumerate(bundle_files, start=1):
            log.info(
                f"\n=== Processing bundle {bundle_index} of {len(bundle_files)}: {bundle_path.name} ==="
            )
            sys.stdout.flush()  # Ensure immediate output for real-time streaming
            report = self._process_bundle(
                bundle_path,
                css_service=css_service,
                texture_service=texture_service,
                font_service=font_service,
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

            font_replacements_total += report.font_replacements
            if not self.options.dry_run and report.font_replacements > 0:
                font_bundles_written += 1

            bundle_reports.append(report)

        # Completion summary
        log.info(f"\n✅ Completed processing {len(bundle_files)} bundle(s)")
        log.info(f"   CSS bundles modified: {css_bundles_modified}")
        log.info(f"   Texture replacements: {texture_replacements_total}")
        if texture_bundles_written > 0:
            log.info(f"   Texture bundles written: {texture_bundles_written}")
        sys.stdout.flush()

        # Final cleanup
        gc.collect()

        return PipelineResult(
            bundle_reports=bundle_reports,
            css_bundles_modified=css_bundles_modified,
            texture_replacements_total=texture_replacements_total,
            texture_bundles_written=texture_bundles_written,
            font_replacements_total=font_replacements_total,
            font_bundles_written=font_bundles_written,
            bundles_requested=bundles_requested,
            summary_lines=summary_lines,
        )

    @staticmethod
    def _bundle_sort_key(path: Path) -> Tuple[int, str]:
        name_lower = path.name.lower()
        if "spriteatlas" in name_lower:
            return (0, name_lower)
        if "atlas" in name_lower:
            return (1, name_lower)
        return (2, name_lower)

    def _sorted_bundle_files(self, bundle_files: List[Path]) -> List[Path]:
        if len(bundle_files) <= 1:
            return list(bundle_files)
        return sorted(bundle_files, key=self._bundle_sort_key)

    def _process_bundle(
        self,
        bundle_path: Path,
        *,
        css_service: CssPatchService,
        texture_service: Optional[TextureSwapService],
        font_service: Optional[FontSwapService],
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
            backup_path = bundle_path.with_suffix(bundle_path.suffix + f".{ts}.bak")
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
                    bundle_ctx, candidate_assets=candidate_assets
                )
            else:
                bundle_ctx.load()
                report = PatchReport(
                    bundle_ctx.bundle_path, dry_run=self.options.dry_run
                )

            if texture_service:
                if bundle_index is None:
                    bundle_index = load_cached_bundle_index(
                        self.css_dir,
                        bundle_path,
                        skin_cache_dir=skin_cache_dir,
                    )
                texture_names = gather_texture_names_from_index(bundle_index)
                should_swap = should_swap_textures(
                    bundle_name=bundle_path.name,
                    texture_names=texture_names,
                    target_names=target_names_from_map,
                    replace_stems=replace_stems,
                    want_icons=want_icons,
                    want_backgrounds=want_bgs,
                )
                has_pending_jobs = texture_service.has_pending_jobs(bundle_path.name)
                if should_swap or has_pending_jobs:
                    try:
                        texture_service.apply(
                            bundle_ctx,
                            self.css_dir,
                            self.out_dir,
                            report,
                        )
                    except Exception as exc:
                        log.warning(f"[WARN] Texture swap skipped due to error: {exc}")
                else:
                    log.debug(
                        "[TEXTURE] Prefilter: skipping bundle with no matching names or pending sprite rebinds."
                    )

            # Font replacement
            if font_service:
                try:
                    font_service.apply(
                        bundle_ctx,
                        self.css_dir,
                        report,
                    )
                except Exception as exc:
                    log.warning(f"[WARN] Font swap skipped due to error: {exc}")

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
