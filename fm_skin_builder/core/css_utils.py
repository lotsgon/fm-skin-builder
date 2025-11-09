from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .logger import get_logger

log = get_logger(__name__)

__all__ = [
    "load_css_vars",
    "load_css_selector_overrides",
    "hex_to_rgba",
    "build_selector_from_parts",
    "serialize_stylesheet_to_uss",
    "clean_for_json",
]


_HEX_SHORTHAND_PATTERN = re.compile(r"^#([0-9a-fA-F]{3,4})$")
_HEX_FULL_PATTERN = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB_PATTERN = re.compile(r"^rgba?\(([^)]+)\)$", re.IGNORECASE)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _parse_rgb_component(token: str) -> Optional[int]:
    token = token.strip()
    if token.endswith("%"):
        try:
            percent = float(token[:-1].strip())
        except ValueError:
            return None
        percent = _clamp(percent, 0.0, 100.0)
        return int(round((percent / 100.0) * 255))
    try:
        value = float(token)
    except ValueError:
        return None
    # Treat integers up to 255 as 0-255 range. If the token looks like a float between 0-1, scale.
    if value <= 1.0 and ("." in token or token.strip().startswith("0")):
        value = value * 255.0
    return int(round(_clamp(value, 0.0, 255.0)))


def _parse_alpha_component(token: str) -> float:
    token = token.strip()
    if token.endswith("%"):
        try:
            percent = float(token[:-1].strip())
        except ValueError:
            return 1.0
        percent = _clamp(percent, 0.0, 100.0)
        return percent / 100.0
    try:
        value = float(token)
    except ValueError:
        return 1.0
    if value > 1.0:
        value = value / 255.0
    return _clamp(value, 0.0, 1.0)


def _expand_shorthand_hex(raw: str) -> str:
    chars = list(raw)
    expanded = "".join(c * 2 for c in chars)
    return expanded


def normalize_css_color(raw_value: str) -> Optional[str]:
    """Normalise CSS colours (hex/rgb/rgba) to #RRGGBB or #RRGGBBAA strings."""

    value = raw_value.strip()
    if not value:
        return None

    match = _HEX_SHORTHAND_PATTERN.match(value)
    if match:
        expanded = _expand_shorthand_hex(match.group(1))
        if len(expanded) == 6:
            return f"#{expanded.upper()}"
        if len(expanded) == 8:
            return f"#{expanded.upper()}"

    match = _HEX_FULL_PATTERN.match(value)
    if match:
        return f"#{match.group(1).upper()}"

    match = _RGB_PATTERN.match(value)
    if match:
        components = [token.strip() for token in match.group(1).split(",")]
        if len(components) not in (3, 4):
            return None
        r = _parse_rgb_component(components[0])
        g = _parse_rgb_component(components[1])
        b = _parse_rgb_component(components[2])
        if None in (r, g, b):
            return None
        a = 1.0
        if len(components) == 4:
            a = _parse_alpha_component(components[3])
        alpha_byte = int(round(_clamp(a, 0.0, 1.0) * 255))
        if alpha_byte == 255:
            return f"#{r:02X}{g:02X}{b:02X}"
        return f"#{r:02X}{g:02X}{b:02X}{alpha_byte:02X}"

    return None


def load_css_vars(path: Path) -> Dict[str, str]:
    """Parse a .css/.uss file for `--var: <color>;` pairs with hex/rgb/rgba support."""

    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"--([\w-]+)\s*:\s*([^;]+);", text)
    css: Dict[str, str] = {}
    for name, value in matches:
        normalised = normalize_css_color(value)
        if not normalised:
            log.warning(
                "Skipping unsupported CSS colour '%s' for --%s in %s", value.strip(), name, path)
            continue
        css[f"--{name}"] = normalised
    log.info("🎨 Loaded %s CSS variables from %s", len(css), path)
    return css


def load_css_selector_overrides(path: Path) -> Dict[Tuple[str, str], str]:
    """Parse selector/property -> colour pairs (hex/rgb/rgba)."""

    text = path.read_text(encoding="utf-8")
    selector_blocks = re.findall(r"(\.[\w-]+)\s*\{([^}]*)\}", text)
    selector_overrides: Dict[Tuple[str, str], str] = {}
    for selector, block in selector_blocks:
        props = re.findall(
            r"([\w-]+)\s*:\s*([^;\n]+?)(?:;|\s*(?=\n|$))",
            block,
        )
        for prop, value in props:
            normalised = normalize_css_color(value)
            if not normalised:
                continue
            key = (selector.strip(), prop.strip())
            selector_overrides[key] = normalised
            selector_overrides[(key[0].lstrip("."), key[1])] = normalised
    return selector_overrides


def hex_to_rgba(hex_str: str) -> Tuple[float, float, float, float]:
    """Convert #RRGGBB or #RRGGBBAA to 0-1 floats."""

    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = _expand_shorthand_hex(s)
    elif len(s) == 4:
        s = _expand_shorthand_hex(s)
    r = int(s[0:2], 16) / 255.0
    g = int(s[2:4], 16) / 255.0
    b = int(s[4:6], 16) / 255.0
    a = int(s[6:8], 16) / 255.0 if len(s) == 8 else 1.0
    return r, g, b, a


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
        data, "m_ComplexSelectors"
    ) else []

    color_properties = {
        "color",
        "background-color",
        "border-color",
        "-unity-background-image-tint-color",
    }
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
                            f"  {prop_name}: {color_to_hex(col)}; /* {comment}, src=colors */"
                        )
                continue
            for val in values:
                value_type = getattr(val, "m_ValueType", None)
                value_index = getattr(val, "valueIndex", None)
                comment = f"rule={rule_idx}, type={value_type}, index={value_index}"
                if value_type == 3 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    lines.append(
                        f"  {prop_name}: var({varname}); /* {comment}, src=strings */"
                    )
                elif value_type == 8 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    varname = _re.sub(r"^-+", "--", varname)
                    lines.append(
                        f"  {prop_name}: {varname}; /* {comment}, src=strings */"
                    )
                elif value_type == 2 and 0 <= value_index < len(floats):
                    val_float = floats[value_index]
                    if prop_name in color_properties:
                        lines.append(
                            f"  /* {prop_name}: {val_float}; [SKIPPED: not valid CSS color] {comment}, src=floats */"
                        )
                    else:
                        lines.append(
                            f"  {prop_name}: {val_float}; /* {comment}, src=floats */"
                        )
                elif value_type == 10 and 0 <= value_index < len(strings):
                    varname = strings[value_index]
                    varname = _re.sub(r"^-+", "--", varname)
                    lines.append(
                        f"  {prop_name}: {varname}; /* {comment}, src=strings */"
                    )
                else:
                    lines.append(
                        f"  {prop_name}: {value_index}; /* {comment}, src=unknown */"
                    )
        lines.append("}")
    return "\n".join(lines)


def clean_for_json(obj, seen=None, max_depth: int = 10):
    """Recursively convert UnityPy objects to JSON-serializable structures."""
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
            "m_ValueType": int(getattr(obj, "m_ValueType"))
            if getattr(obj, "m_ValueType") is not None
            else None,
            "valueIndex": int(getattr(obj, "valueIndex"))
            if getattr(obj, "valueIndex") is not None
            else None,
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

    if all(hasattr(obj, c) for c in ("r", "g", "b", "a")) and type(obj).__name__.lower().startswith(
        "color"
    ):
        return {
            "r": float(obj.r),
            "g": float(obj.g),
            "b": float(obj.b),
            "a": float(obj.a),
        }

    if type(obj).__name__ == "PPtr" or (
        hasattr(obj, "m_FileID") and hasattr(obj, "m_PathID")
    ):
        return {
            "m_FileID": int(getattr(obj, "m_FileID", 0)),
            "m_PathID": int(getattr(obj, "m_PathID", 0)),
        }

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
        return {
            str(k): clean_for_json(v, seen, max_depth - 1)
            for k, v in obj.items()
            if k != "object_reader"
        }
    if hasattr(obj, "__dict__"):
        return {
            k: clean_for_json(v, seen, max_depth - 1)
            for k, v in obj.__dict__.items()
            if not k.startswith("_") and k != "object_reader"
        }
    return str(obj)
