from __future__ import annotations
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any, Set
import re
import json
import os
import shutil
import UnityPy

from .logger import get_logger
from .cache import load_or_cache_config, cache_dir

log = get_logger(__name__)


# -----------------------------
# CSS/USS parsing helpers
# -----------------------------

def load_css_vars(path: Path) -> Dict[str, str]:
    """Parse a .css/.uss file for --var: #hex; pairs."""
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6,8});", text)
    css = {f"--{k}": v for k, v in matches}
    log.info(f"🎨 Loaded {len(css)} CSS variables from {path}")
    return css


def load_css_selector_overrides(path: Path) -> Dict[Tuple[str, str], str]:
    """Parse a .css/.uss file for selector/property -> #hex pairs (e.g., .green { color: #00D3E7; })."""
    text = path.read_text(encoding="utf-8")
    selector_blocks = re.findall(r"(\.[\w-]+)\s*\{([^}]*)\}", text)
    selector_overrides: Dict[Tuple[str, str], str] = {}
    for selector, block in selector_blocks:
        props = re.findall(r"([\w-]+)\s*:\s*(#[0-9a-fA-F]{6,8});", block)
        for prop, hexval in props:
            selector_overrides[(selector.strip(), prop.strip())] = hexval
            selector_overrides[(selector.strip().lstrip(
                "."), prop.strip())] = hexval
    return selector_overrides


def hex_to_rgba(hex_str: str) -> Tuple[float, float, float, float]:
    """Convert #RRGGBB or #RRGGBBAA to 0-1 floats."""
    s = hex_str.lstrip("#")
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    a = int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0
    return r, g, b, a


# -----------------------------
# Debug export helpers
# -----------------------------

def build_selector_from_parts(parts) -> str:
    selector = ""
    for part in parts:
        val = getattr(part, "m_Value", "")
        ptype = getattr(part, "m_Type", 0)
        if ptype == 2:
            selector += f"#{val}"
        elif ptype == 3:
            selector += f".{val}"
        elif ptype in (4, 5):
            selector += f":{val}"
        else:
            selector += str(val)
    return selector or "*"


def serialize_stylesheet_to_uss(data) -> str:
    """Serialize a StyleSheet MonoBehaviour to a .uss-like text for debugging."""
    import re as _re

    def color_to_hex(c):
        r = int(round(c.r * 255))
        g = int(round(c.g * 255))
        b = int(round(c.b * 255))
        if hasattr(c, "a") and c.a < 1.0:
            return f"rgba({r}, {g}, {b}, {c.a:.2f})"
        return f"#{r:02X}{g:02X}{b:02X}"

    strings = getattr(data, "strings", [])
    colors = getattr(data, "colors", [])
    floats = getattr(data, "floats", []) if hasattr(data, "floats") else []
    rules = getattr(data, "m_Rules", [])
    selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
        data, "m_ComplexSelectors") else []

    color_properties = {"color", "background-color",
                        "border-color", "-unity-background-image-tint-color"}
    lines: List[str] = []

    for sel in selectors:
        rule_idx = getattr(sel, "ruleIndex", None)
        if rule_idx is None or rule_idx >= len(rules):
            continue
        selector_text = ""
        if hasattr(sel, "m_Selectors") and sel.m_Selectors:
            parts = sel.m_Selectors[0].m_Parts if sel.m_Selectors[0].m_Parts else [
            ]
            for part in parts:
                val = getattr(part, "m_Value", "")
                ptype = getattr(part, "m_Type", 0)
                if ptype == 2:
                    selector_text += f"#{val}"
                elif ptype == 3:
                    selector_text += f".{val}"
                elif ptype in (4, 5):
                    selector_text += f":{val}"
                else:
                    selector_text += str(val)
        selector_text = selector_text or "*"
        lines.append(f"{selector_text} {{")
        rule = rules[rule_idx]
        for prop in getattr(rule, "m_Properties", []):
            prop_name = getattr(prop, "m_Name", "")
            values = list(getattr(prop, "m_Values", []))
            type4_vals = [v for v in values if getattr(
                v, "m_ValueType", None) == 4]
            if type4_vals:
                for val in type4_vals:
                    value_type = getattr(val, "m_ValueType", None)
                    value_index = getattr(val, "valueIndex", None)
                    comment = f"rule={rule_idx}, type={value_type}, index={value_index}"
                    if value_type == 4 and 0 <= value_index < len(colors):
                        col = colors[value_index]
                        lines.append(
                            f"  {prop_name}: {color_to_hex(col)}; /* {comment}, src=colors */")
                continue
            for val in values:
                value_type = getattr(val, "m_ValueType", None)
                value_index = getattr(val, "valueIndex", None)
                comment = f"rule={rule_idx}, type={value_type}, index={value_index}"
                if value_type == 3 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    lines.append(
                        f"  {prop_name}: var({varname}); /* {comment}, src=strings */")
                elif value_type == 8 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    varname = _re.sub(r"^-+", "--", varname)
                    lines.append(
                        f"  {prop_name}: {varname}; /* {comment}, src=strings */")
                elif value_type == 2 and 0 <= value_index < len(floats):
                    val_float = floats[value_index]
                    if prop_name in color_properties:
                        lines.append(
                            f"  /* {prop_name}: {val_float}; [SKIPPED: not valid CSS color] {comment}, src=floats */")
                    else:
                        lines.append(
                            f"  {prop_name}: {val_float}; /* {comment}, src=floats */")
                elif value_type == 10 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    varname = _re.sub(r"^-+", "--", varname)
                    lines.append(
                        f"  {prop_name}: {varname}; /* {comment}, src=strings */")
                else:
                    lines.append(
                        f"  {prop_name}: {value_index}; /* {comment}, src=unknown */")
        lines.append("}")
    return "\n".join(lines)


def clean_for_json(obj, seen=None, max_depth: int = 10):
    """Recursively convert UnityPy objects to JSON-serializable structures for debugging export."""
    if seen is None:
        seen = set()
    if max_depth <= 0:
        return None
    obj_id = id(obj)
    if obj_id in seen:
        return None
    seen.add(obj_id)

    if hasattr(obj, "m_ValueType") and hasattr(obj, "valueIndex"):
        return {
            "m_ValueType": int(getattr(obj, "m_ValueType")) if getattr(obj, "m_ValueType") is not None else None,
            "valueIndex": int(getattr(obj, "valueIndex")) if getattr(obj, "valueIndex") is not None else None,
        }

    selector_keys = ["m_Specificity", "m_Type",
                     "m_PreviousRelationship", "ruleIndex"]
    if any(hasattr(obj, k) for k in selector_keys):
        result = {}
        for k in getattr(obj, "__dict__", {}).keys():
            if k.startswith("_") or k == "object_reader":
                continue
            v = getattr(obj, k)
            if k in selector_keys:
                result[k] = int(v) if v is not None else None
            else:
                result[k] = clean_for_json(v, seen, max_depth - 1)
        return result

    if all(hasattr(obj, c) for c in ("r", "g", "b", "a")) and type(obj).__name__.lower().startswith("color"):
        return {"r": float(obj.r), "g": float(obj.g), "b": float(obj.b), "a": float(obj.a)}

    if type(obj).__name__ == "PPtr" or (hasattr(obj, "m_FileID") and hasattr(obj, "m_PathID")):
        return {"m_FileID": int(getattr(obj, "m_FileID", 0)), "m_PathID": int(getattr(obj, "m_PathID", 0))}

    if hasattr(obj, "__dict__") and hasattr(obj, "type") and hasattr(obj.type, "name"):
        result = {}
        for k, v in obj.__dict__.items():
            if k.startswith("_") or k == "object_reader":
                continue
            result[k] = clean_for_json(v, seen, max_depth - 1)
        return result

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        return [clean_for_json(x, seen, max_depth - 1) for x in obj]
    if isinstance(obj, dict):
        return {str(k): clean_for_json(v, seen, max_depth - 1) for k, v in obj.items() if k != "object_reader"}
    if hasattr(obj, "__dict__"):
        return {k: clean_for_json(v, seen, max_depth - 1) for k, v in obj.__dict__.items() if not k.startswith("_") and k != "object_reader"}
    return str(obj)


# -----------------------------
# Core patcher
# -----------------------------

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

    def patch_bundle_file(self, bundle_path: Path, out_dir: Path, candidate_assets: Optional[Set[str]] = None) -> None:
        env = UnityPy.load(str(bundle_path))
        bundle_name = bundle_path.name

        patched_vars = 0
        patched_direct = 0
        found_styles = 0
        any_changes = False
        changed_asset_names: Set[str] = set()
        # Track selector override touches per (selector, prop) across assets for conflict surfacing
        self._selector_touches: Dict[Tuple[str, str], Set[str]] = {}

        # Defer creating debug dir until we actually have something to export

        log.info(f"🔍 Scanning bundle: {bundle_name}")

        original_uss = []
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            data = obj.read()
            if not hasattr(data, "colors") or not hasattr(data, "strings"):
                continue
            name = getattr(data, "m_Name", "UnnamedStyleSheet")
            # If we have a candidate filter, skip non-candidates
            if candidate_assets is not None and name not in candidate_assets:
                continue
            will_patch = self._will_patch(data)
            if self.debug_export_dir and will_patch and not self.dry_run:
                # ensure dir exists right before first export
                self.debug_export_dir.mkdir(parents=True, exist_ok=True)
                self._export_debug_original(name, data)
            original_uss.append((obj, data, name))

        for obj, data, name in original_uss:
            found_styles += 1
            pv, pd, changed = self._apply_patches_to_stylesheet(name, data)
            patched_vars += pv
            patched_direct += pd
            if changed:
                # Only persist modified typetrees
                any_changes = True
                changed_asset_names.add(name)
                if not self.dry_run:
                    data.save()

        if not any_changes:
            log.info(
                "No changes detected; skipping bundle write and debug outputs.")
            return

        # Prepare conflict/touch summary for selector overrides across assets
        multi_asset_touches: List[Tuple[Tuple[str, str], int]] = []
        if hasattr(self, "_selector_touches"):
            for k, assets in self._selector_touches.items():
                if isinstance(assets, set) and len(assets) > 1:
                    multi_asset_touches.append((k, len(assets)))

        if self.dry_run:
            log.info("\n🧾 Summary:")
            log.info(f"  Stylesheets found: {found_styles}")
            log.info(f"  Assets modified: {len(changed_asset_names)}")
            log.info(f"  Variables patched: {patched_vars}")
            log.info(f"  Direct colors patched: {patched_direct}")
            if multi_asset_touches:
                log.info("  Selector overrides affecting multiple assets:")
                for (sel, prop), n in multi_asset_touches:
                    log.info(f"    {sel} / {prop}: {n} assets")
            log.info("[DRY-RUN] No files were written. Use without --dry-run to apply changes.")
            return

        out_dir.mkdir(parents=True, exist_ok=True)
        name, ext = os.path.splitext(bundle_name)
        out_file = out_dir / f"{name}_modified{ext}"
        orig_out_file = out_dir / f"{name}{ext}"

        try:
            log.info(
                f"[INFO] Writing modified bundle to: {out_file} (env.file.save())")
            with open(out_file, "wb") as f:
                f.write(env.file.save())
            saved = True
        except Exception as e:
            log.error(f"[ERROR] Failed to save modified bundle: {e}")
            saved = False

        if orig_out_file.exists():
            try:
                orig_out_file.unlink()
                log.info(
                    f"[CLEANUP] Removed stray original bundle: {orig_out_file}")
            except Exception as cleanup_err:
                log.warning(
                    f"[WARN] Could not remove stray original bundle: {orig_out_file}: {cleanup_err}")

        cwd_orig_file = Path.cwd() / f"{name}{ext}"
        if cwd_orig_file != orig_out_file and cwd_orig_file.exists():
            try:
                cwd_orig_file.unlink()
                log.info(
                    f"[CLEANUP] Removed stray original bundle from CWD: {cwd_orig_file}")
            except Exception as cleanup_err:
                log.warning(
                    f"[WARN] Could not remove stray original bundle from CWD: {cwd_orig_file}: {cleanup_err}")

        if not saved:
            log.error(
                "[ERROR] Could not save patched bundle. The bundle may be corrupt or use unsupported compression.")
            return

        log.info("\n🧾 Summary:")
        log.info(f"  Stylesheets found: {found_styles}")
        log.info(f"  Assets modified: {len(changed_asset_names)}")
        log.info(f"  Variables patched: {patched_vars}")
        log.info(f"  Direct colors patched: {patched_direct}")
        if multi_asset_touches:
            log.info("  Selector overrides affecting multiple assets:")
            for (sel, prop), n in multi_asset_touches:
                log.info(f"    {sel} / {prop}: {n} assets")
        log.info(f"💾 Saved patched bundle(s) → {out_dir}")
        if self.debug_export_dir:
            log.info(f"📝 Exported .uss files to {self.debug_export_dir}")

    # -----------------------------
    # internals
    # -----------------------------

    def _will_patch(self, data) -> bool:
        # Check var-based direct property patches
        for rule in getattr(data, "m_Rules", []):
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if prop_name in self.css_vars:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(getattr(data, "colors", [])):
                                hex_val = self.css_vars[prop_name]
                                r, g, b, a = hex_to_rgba(hex_val)
                                col = data.colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
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
                        allowed = any((sv, prop_name) in self.selector_props_filter for sv in sel_variants)
                        if not allowed:
                            continue
                    elif self.selectors_filter is not None:
                        # Require selector to be in allowed set
                        allowed = any(sv in self.selectors_filter for sv in sel_variants)
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
                if prop_name in self.css_vars:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(colors):
                                hex_val = self.css_vars[prop_name]
                                r, g, b, a = hex_to_rgba(hex_val)
                                col = colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                    col.r, col.g, col.b, col.a = r, g, b, a
                                    patched_vars += 1
                                    direct_property_patched_indices.add(
                                        value_index)
                                    log.info(
                                        f"  [PATCHED - direct property] {name}: {prop_name} (color index {value_index}) → {hex_val}"
                                    )
                                    changed = True

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
                            found_type4 = False
                            for val in getattr(prop, "m_Values", []):
                                if getattr(val, "m_ValueType", None) == 4:
                                    found_type4 = True
                                    value_index = getattr(
                                        val, "valueIndex", None)
                                    if value_index is not None and 0 <= value_index < len(colors):
                                        r, g, b, a = hex_to_rgba(hex_val)
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
                                        # Record touch for conflict surfacing (normalize key to tuple)
                                        try:
                                            touches = getattr(self, "_selector_touches", None)
                                            if touches is not None:
                                                norm_sel = key[0]
                                                touches.setdefault((norm_sel if norm_sel.startswith('.') else norm_sel, prop_name), set()).add(name)
                                        except Exception:
                                            pass
                            if not found_type4:
                                log.warning(
                                    f"  [WARN] No m_ValueType==4 found for {key} in {name}."
                                )

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


# -----------------------------
# Orchestration helpers (dirs)
# -----------------------------

def collect_css_from_dir(css_dir: Path) -> Tuple[Dict[str, str], Dict[Tuple[str, str], str]]:
    """Collect CSS variable and selector overrides from a directory.

    If css_dir looks like a skin folder (has config.json), also scan its 'colours' subfolder.
    """
    css_vars: Dict[str, str] = {}
    selector_overrides: Dict[Tuple[str, str], str] = {}

    files: List[Path] = []
    if (css_dir / "config.json").exists():
        # skin root
        colours = css_dir / "colours"
        if colours.exists():
            files.extend(sorted(colours.glob("*.uss")))
            files.extend(sorted(colours.glob("*.css")))
        # also allow overrides at root
        files.extend(sorted(css_dir.glob("*.uss")))
        files.extend(sorted(css_dir.glob("*.css")))
    else:
        files.extend(sorted(css_dir.glob("*.uss")))
        files.extend(sorted(css_dir.glob("*.css")))

    for f in files:
        try:
            css_vars.update(load_css_vars(f))
            selector_overrides.update(load_css_selector_overrides(f))
        except Exception as e:
            log.warning(f"Failed to parse {f}: {e}")

    log.info(
        f"Total CSS vars: {len(css_vars)}, selector overrides: {len(selector_overrides)} from {len(files)} files")
    return css_vars, selector_overrides


def load_targeting_hints(css_dir: Path) -> Tuple[Optional[Set[str]], Optional[Set[str]], Optional[Set[Tuple[str, str]]]]:
    """Load optional targeting hints from a skin or CSS directory.

    Supports a simple hints.txt file with lines like:
      # comments allowed with '#'
      asset: DialogStyles
      asset: CommonStyles, ExtraStyles
      selector: .green
      selector: .green color

    Returns (assets, selectors, selector_props) where each element is either a set or None if not provided.
    - assets: set of asset names to include. If provided, we only consider these assets.
    - selectors: set of selector strings (with or without '.') to include for selector/property overrides.
    - selector_props: set of (selector, property) tuples to include for selector/property overrides.
    """
    # Determine root
    root = css_dir
    hints_path = root / "hints.txt"
    if not hints_path.exists():
        return None, None, None

    assets: Set[str] = set()
    selectors: Set[str] = set()
    selector_props: Set[Tuple[str, str]] = set()

    try:
        for raw in hints_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Remove trailing inline comment
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            # asset: name[, name]
            m_asset = re.match(r"^asset\s*[:=]\s*(.+)$", line, re.IGNORECASE)
            if m_asset:
                names = [x.strip() for x in re.split(r",|;", m_asset.group(1)) if x.strip()]
                assets.update(names)
                continue
            # selector: .sel [prop]
            m_sel = re.match(r"^selector\s*[:=]\s*(.+)$", line, re.IGNORECASE)
            if m_sel:
                rest = m_sel.group(1).strip()
                # If rest contains whitespace, treat as "<selector> <prop>"
                if " " in rest:
                    sel, prop = rest.split(None, 1)
                    selectors.add(sel.strip())
                    selector_props.add((sel.strip(), prop.strip()))
                else:
                    selectors.add(rest)
                continue
    except Exception as e:
        log.warning(f"Failed to parse targeting hints at {hints_path}: {e}")

    return (assets or None, selectors or None, selector_props or None)


def infer_bundle_files(css_dir: Path) -> List[Path]:
    """Infer bundle file(s) from skin config if available."""
    bundles: List[Path] = []
    cfg = css_dir / "config.json"
    if cfg.exists():
        try:
            model = load_or_cache_config(css_dir)
            target = Path(model.target_bundle)
            if target.exists():
                bundles.append(target)
                log.info(f"Inferred bundle from config: {target}")
        except Exception as e:
            log.warning(f"Could not infer bundle from config: {e}")
    return bundles


def run_patch(css_dir: Path, out_dir: Path, bundle: Optional[Path] = None, patch_direct: bool = False, debug_export: bool = False, backup: bool = False, dry_run: bool = False, use_scan_cache: bool = True, refresh_scan_cache: bool = False) -> None:
    """High-level entry to patch bundles based on CSS in css_dir.

    - css_dir: skin folder or directory containing .uss/.css files
    - out_dir: where to write modified bundles
    - bundle: optional bundle file or directory; if omitted we try to infer from config in css_dir
    - patch_direct: also patch inlined color literals
    - debug_export: export original/patched .uss and JSON alongside for inspection
    - backup: backup original bundle(s) next to their paths
    """
    css_vars, selector_overrides = collect_css_from_dir(css_dir)
    # Optional targeting hints
    hints_assets, hints_selectors, hints_selector_props = load_targeting_hints(css_dir)
    debug_dir = (out_dir / "debug_uss") if debug_export else None
    patcher = CssPatcher(
        css_vars,
        selector_overrides,
        patch_direct=patch_direct,
        debug_export_dir=debug_dir,
        dry_run=dry_run,
        selectors_filter=hints_selectors,
        selector_props_filter=hints_selector_props,
    )

    bundle_files: List[Path] = []
    if bundle is not None:
        if bundle.is_dir():
            bundle_files = [
                p for p in bundle.iterdir() if p.suffix == ".bundle"]
        else:
            bundle_files = [bundle]
    else:
        bundle_files = infer_bundle_files(css_dir)
        if not bundle_files:
            log.error(
                "No bundle specified and none could be inferred from config. Provide --bundle.")
            return

    # Build candidate asset filters from cached scan index if available
    skin_is_known = (css_dir / "config.json").exists()
    cache_candidates: Dict[Path, Optional[Set[str]]]= {}
    if use_scan_cache and skin_is_known:
        # if refresh flag, generate fresh cache
        try:
            cdir = cache_dir(root=css_dir.parent.parent) / css_dir.name
            cdir.mkdir(parents=True, exist_ok=True)
            for b in bundle_files:
                cand = _load_or_refresh_scan_cache(cdir, css_dir, b, refresh=refresh_scan_cache, css_vars=css_vars, selector_overrides=selector_overrides, patch_direct=patch_direct)
                cache_candidates[b] = cand
        except Exception as e:
            log.debug(f"Scan cache unavailable: {e}")

    for b in bundle_files:
        if backup:
            ts = os.environ.get("FM_SKIN_BACKUP_TS") or "backup"
            backup_path = b.with_suffix(b.suffix + f".{ts}.bak")
            try:
                shutil.copy2(b, backup_path)
                log.info(f"🗄️ Backed up original bundle to {backup_path}")
            except Exception as e:
                log.warning(f"Could not backup {b}: {e}")
        log.info(f"\n=== Patching bundle: {b} ===")
        # Combine candidate assets from scan cache and hints
        cand = cache_candidates.get(b)
        if hints_assets:
            if cand is None:
                cand = set(hints_assets)
            else:
                cand = set(cand) & set(hints_assets)
        if cand is not None and len(cand) == 0:
            log.info(f"Hint filter excluded all assets for {b.name}; skipping bundle.")
            continue
        patcher.patch_bundle_file(b, out_dir, candidate_assets=cand)


# -----------------------------
# Scan cache helpers (optional)
# -----------------------------

SCAN_INDEX_VERSION = 1


def _bundle_fingerprint(path: Path) -> Dict[str, Any]:
    try:
        st = path.stat()
        return {"path": str(path), "mtime": int(st.st_mtime), "size": int(st.st_size)}
    except Exception:
        return {"path": str(path), "mtime": None, "size": None}


def _cache_index_path(cache_skin_dir: Path, bundle: Path) -> Path:
    return cache_skin_dir / f"{bundle.stem}.index.json"


def _is_index_valid(idx: Dict[str, Any], bundle: Path) -> bool:
    meta = idx.get("_meta", {})
    if meta.get("version") != SCAN_INDEX_VERSION:
        return False
    fp = meta.get("fingerprint", {})
    st = bundle.stat()
    return (
        fp.get("path") == str(bundle)
        and isinstance(fp.get("mtime"), int)
        and isinstance(fp.get("size"), int)
        and fp.get("mtime") == int(st.st_mtime)
        and fp.get("size") == int(st.st_size)
    )


def _load_index(cache_skin_dir: Path, bundle: Path) -> Optional[Dict[str, Any]]:
    p = _cache_index_path(cache_skin_dir, bundle)
    if not p.exists():
        return None
    try:
        idx = json.loads(p.read_text(encoding="utf-8"))
        if _is_index_valid(idx, bundle):
            log.debug(f"Using cached scan index: {p}")
            return idx
    except Exception:
        return None
    return None


def _save_index(cache_skin_dir: Path, bundle: Path, index: Dict[str, Any]) -> Path:
    p = _cache_index_path(cache_skin_dir, bundle)
    idx = dict(index)  # shallow copy
    idx["_meta"] = {"version": SCAN_INDEX_VERSION, "fingerprint": _bundle_fingerprint(bundle)}
    p.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _refresh_index(cache_skin_dir: Path, bundle: Path) -> Dict[str, Any]:
    # Reuse inspector to compute a fresh index without USS export
    from . import bundle_inspector  # local import to avoid circular dependency
    tmp_out = cache_skin_dir / f"__scan__{bundle.stem}"
    tmp_out.mkdir(parents=True, exist_ok=True)
    try:
        index = bundle_inspector.scan_bundle(bundle, tmp_out, export_uss=False)
        # Read written index and then persist a cached copy with metadata
        tmp_idx_path = tmp_out / "bundle_index.json"
        if tmp_idx_path.exists():
            index = json.loads(tmp_idx_path.read_text(encoding="utf-8"))
        _save_index(cache_skin_dir, bundle, index)
        return index
    finally:
        # Clean up temporary folder best-effort
        try:
            for child in tmp_out.iterdir():
                try:
                    child.unlink()
                except Exception:
                    pass
            tmp_out.rmdir()
        except Exception:
            pass


def _load_or_refresh_scan_cache(cache_skin_dir: Path, css_dir: Path, bundle: Path, refresh: bool, css_vars: Dict[str, str], selector_overrides: Dict[Tuple[str, str], str], patch_direct: bool) -> Optional[Set[str]]:
    # Ensure we have a valid index
    index: Optional[Dict[str, Any]] = None
    if not refresh:
        index = _load_index(cache_skin_dir, bundle)
    if index is None:
        index = _refresh_index(cache_skin_dir, bundle)

    # Build candidate asset set based on requested changes
    # If patch_direct is True, skip prefiltering to remain safe
    if patch_direct:
        return None
    candidates: Set[str] = set()
    var_map = index.get("var_map", {})
    sel_map = index.get("selector_map", {})
    # Variables
    for var in css_vars.keys():
        if var in var_map:
            for hit in var_map[var]:
                asset = hit.get("asset")
                if asset:
                    candidates.add(asset)
    # Selector overrides
    for (selector, prop), _hex in selector_overrides.items():
        # Normalize selector variants (".green" and "green")
        keys = [selector, selector.lstrip(".")]
        for sel in keys:
            props = sel_map.get(sel)
            if isinstance(props, dict):
                # If a specific property is targeted, require that
                if prop in props:
                    for hit in props[prop]:
                        asset = hit.get("asset")
                        if asset:
                            candidates.add(asset)
                else:
                    # If property not present in index, fall back to whole selector
                    for plist in props.values():
                        for hit in plist:
                            asset = hit.get("asset")
                            if asset:
                                candidates.add(asset)

    # If no candidates found, return None to avoid accidentally skipping valid updates
    return candidates if candidates else None
