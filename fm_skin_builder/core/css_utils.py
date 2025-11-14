from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .logger import get_logger

log = get_logger(__name__)

__all__ = [
    "load_css_vars",
    "load_css_selector_overrides",
    "load_css_properties",
    "load_css_selector_properties",
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
                "Skipping unsupported CSS colour '%s' for --%s in %s",
                value.strip(),
                name,
                path,
            )
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


def load_css_properties(path: Path) -> Dict[str, Any]:
    """
    Parse a .css/.uss file for all CSS variable declarations (not just colors).

    Returns a dictionary mapping variable names to their values (as strings).
    Values can be colors, floats, keywords, etc.
    """
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"--([\w-]+)\s*:\s*([^;]+);", text)
    properties: Dict[str, Any] = {}

    for name, value in matches:
        value = value.strip()
        if not value:
            continue

        # First try to normalize as color (for backwards compatibility)
        normalised_color = normalize_css_color(value)
        if normalised_color:
            properties[f"--{name}"] = normalised_color
        else:
            # Store the raw value for non-color properties
            # The value will be parsed later based on property context
            properties[f"--{name}"] = value

    log.info("🎨 Loaded %s CSS properties from %s", len(properties), path)
    return properties


def load_css_selector_properties(path: Path) -> Dict[Tuple[str, str], Any]:
    """
    Parse selector/property pairs for all property types (not just colors).

    Returns a dictionary mapping (selector, property) tuples to their values.
    """
    text = path.read_text(encoding="utf-8")
    selector_blocks = re.findall(r"(\.[\w-]+)\s*\{([^}]*)\}", text)
    selector_props: Dict[Tuple[str, str], Any] = {}

    for selector, block in selector_blocks:
        props = re.findall(
            r"([\w-]+)\s*:\s*([^;\n]+?)(?:;|\s*(?=\n|$))",
            block,
        )
        for prop, value in props:
            value = value.strip()
            if not value:
                continue

            # First try to normalize as color (for backwards compatibility)
            normalised_color = normalize_css_color(value)
            if normalised_color:
                value_to_store = normalised_color
            else:
                # Store raw value for non-color properties
                value_to_store = value

            key = (selector.strip(), prop.strip())
            selector_props[key] = value_to_store
            selector_props[(key[0].lstrip("."), key[1])] = value_to_store

    return selector_props


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


def serialize_stylesheet_to_uss(
    data, debug_comments: bool = False, sort_properties: bool = True
) -> str:
    """
    Serialize a StyleSheet MonoBehaviour to a .uss-like text.

    Args:
        data: Unity StyleSheet data
        debug_comments: If True, include debug comments with type/index info
        sort_properties: If True, sort properties in a logical order (position, display, dimensions, etc.)

    Returns:
        USS-formatted string
    """
    from collections import defaultdict
    from typing import List as TList, Tuple as TTuple

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
    selectors = (
        getattr(data, "m_ComplexSelectors", [])
        if hasattr(data, "m_ComplexSelectors")
        else []
    )

    # Unity USS Value Types:
    # Type 1: Keyword (auto, none, center, etc.)
    # Type 2: Float/Dimension (stored in floats array)
    # Type 3: Dimension string (like "10px", "50%") - stored in strings
    # Type 4: Color (stored in colors array)
    # Type 5: Resource path (url(...))
    # Type 6: Asset reference
    # Type 7: Enum (integer values)
    # Type 8: String literal
    # Type 9: Missing asset reference
    # Type 10: Variable name (like "--my-var")
    # Type 11: Function call (like "var(--my-var)")

    # Properties that expect color values
    color_properties = {
        "color",
        "background-color",
        "border-color",
        "border-left-color",
        "border-right-color",
        "border-top-color",
        "border-bottom-color",
        "-unity-background-image-tint-color",
    }

    # Multi-value shorthand properties (space-separated)
    multi_value_shorthands = {
        "margin": 4,  # top right bottom left
        "padding": 4,  # top right bottom left
        "border-width": 4,  # top right bottom left
        "border-radius": 4,  # top-left top-right bottom-right bottom-left
        "border-color": 4,  # top right bottom left
    }

    lines: TList[str] = []

    for sel in selectors:
        rule_idx = getattr(sel, "ruleIndex", None)
        if rule_idx is None or rule_idx >= len(rules):
            continue
        selector_text = ""
        if hasattr(sel, "m_Selectors") and sel.m_Selectors:
            parts = sel.m_Selectors[0].m_Parts if sel.m_Selectors[0].m_Parts else []
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

        # Group all values by property name
        property_values: Dict[str, TList[TTuple[int, int, str]]] = defaultdict(list)
        for prop in getattr(rule, "m_Properties", []):
            prop_name = getattr(prop, "m_Name", "")
            values = list(getattr(prop, "m_Values", []))

            for val in values:
                value_type = getattr(val, "m_ValueType", None)
                value_index = getattr(val, "valueIndex", None)

                if value_type is None or value_index is None:
                    continue

                # Format the value based on its type
                formatted_value = _format_uss_value(
                    value_type, value_index, strings, colors, floats, prop_name
                )

                if formatted_value:
                    property_values[prop_name].append(
                        (value_type, value_index, formatted_value)
                    )

        # Output each property once with the correct value(s)
        # Sort properties in a logical order if requested
        prop_names = property_values.keys()
        if sort_properties:
            prop_names = _sort_properties(list(prop_names))

        for prop_name in prop_names:
            values = property_values[prop_name]

            if len(values) == 0:
                continue

            # Pick the best value(s) for this property
            final_value, comment_info = _pick_best_value(
                prop_name, values, multi_value_shorthands, color_properties
            )

            if debug_comments and comment_info:
                lines.append(f"  {prop_name}: {final_value}; /* {comment_info} */")
            else:
                lines.append(f"  {prop_name}: {final_value};")

        lines.append("}")
    return "\n".join(lines)


def _sort_properties(prop_names: List[str]) -> List[str]:
    """
    Sort CSS properties in a logical order for better readability.

    Order: Position → Display → Flex → Dimensions → Spacing → Border → Background → Text → Transform → Transition → Others
    """
    property_order = {
        # Position (highest priority)
        "position": 0,
        "top": 1,
        "right": 2,
        "bottom": 3,
        "left": 4,
        # Display
        "display": 10,
        "visibility": 11,
        "opacity": 12,
        "overflow": 13,
        # Flexbox
        "flex-direction": 20,
        "flex-wrap": 21,
        "justify-content": 22,
        "align-items": 23,
        "align-self": 24,
        "flex-grow": 25,
        "flex-shrink": 26,
        "flex-basis": 27,
        # Dimensions
        "width": 30,
        "height": 31,
        "min-width": 32,
        "min-height": 33,
        "max-width": 34,
        "max-height": 35,
        # Margin
        "margin": 40,
        "margin-top": 41,
        "margin-right": 42,
        "margin-bottom": 43,
        "margin-left": 44,
        # Padding
        "padding": 50,
        "padding-top": 51,
        "padding-right": 52,
        "padding-bottom": 53,
        "padding-left": 54,
        # Border
        "border-width": 60,
        "border-top-width": 61,
        "border-right-width": 62,
        "border-bottom-width": 63,
        "border-left-width": 64,
        "border-color": 65,
        "border-top-color": 66,
        "border-right-color": 67,
        "border-bottom-color": 68,
        "border-left-color": 69,
        "border-radius": 70,
        "border-top-left-radius": 71,
        "border-top-right-radius": 72,
        "border-bottom-left-radius": 73,
        "border-bottom-right-radius": 74,
        # Background
        "background-color": 80,
        "background-image": 81,
        "-unity-background-image-tint-color": 82,
        "-unity-background-scale-mode": 83,
        # Text/Font
        "color": 90,
        "font-size": 91,
        "-unity-font": 92,
        "-unity-font-definition": 93,
        "-unity-font-style": 94,
        "font-weight": 95,
        "-unity-text-align": 96,
        "-unity-text-outline-width": 97,
        "-unity-text-outline-color": 98,
        "white-space": 99,
        "text-overflow": 100,
        # Transform
        "rotate": 110,
        "scale": 111,
        "translate": 112,
        "transform-origin": 113,
        # Transition
        "transition-property": 120,
        "transition-duration": 121,
        "transition-timing-function": 122,
        "transition-delay": 123,
        # Cursor
        "cursor": 130,
        # Unity-specific (lower priority)
        "-unity-slice-left": 200,
        "-unity-slice-top": 201,
        "-unity-slice-right": 202,
        "-unity-slice-bottom": 203,
        "-unity-paragraph-spacing": 204,
        "-unity-text-overflow-position": 205,
    }

    def get_sort_key(prop: str) -> Tuple[int, str]:
        """Get sort key for a property. Returns (order, property_name)."""
        order = property_order.get(prop, 999)  # Unknown properties at end
        return (order, prop)

    return sorted(prop_names, key=get_sort_key)


def _format_uss_value(
    value_type: int,
    value_index: int,
    strings: List[str],
    colors: List[Any],
    floats: List[float],
    prop_name: str,
) -> Optional[str]:
    """
    Format a Unity USS value based on its type.

    Returns:
        Formatted value string, or None if invalid
    """
    import re as _re

    if value_type == 1:  # Keyword
        # Type 1 uses string index for keyword values
        if 0 <= value_index < len(strings):
            return strings[value_index]
        return None

    elif value_type == 2:  # Float/Dimension
        if 0 <= value_index < len(floats):
            val_float = floats[value_index]
            # Unity stores dimensions as floats (pixels)
            if val_float == int(val_float):
                return f"{int(val_float)}px"
            else:
                return f"{val_float:.2f}px"
        return None

    elif value_type == 3:  # Dimension string (like "10px", "50%", "auto")
        if 0 <= value_index < len(strings):
            return strings[value_index]
        return None

    elif value_type == 4:  # Color
        if 0 <= value_index < len(colors):
            col = colors[value_index]
            r = int(round(col.r * 255))
            g = int(round(col.g * 255))
            b = int(round(col.b * 255))
            if hasattr(col, "a") and col.a < 1.0:
                return f"rgba({r}, {g}, {b}, {col.a:.2f})"
            return f"#{r:02X}{g:02X}{b:02X}"
        return None

    elif value_type == 5:  # Resource path
        if 0 <= value_index < len(strings):
            path = strings[value_index]
            # For very long paths (project:// URIs), quote them for readability
            if path and (
                path.startswith("project://") or path.startswith("resource://")
            ):
                return f'url("{path}")'
            return f"url('{path}')"
        return None

    elif (
        value_type == 7
    ):  # Enum/Resource (Unity stores resource paths as Type 7 sometimes)
        # Check if this is actually a string index pointing to a resource URL
        if 0 <= value_index < len(strings):
            value = strings[value_index]
            # If it's a project:// or resource:// URL, quote it
            if value and (
                value.startswith("project://") or value.startswith("resource://")
            ):
                return f'"{value}"'
        # Otherwise it's an integer enum value
        return str(value_index)

    elif value_type == 8:  # String literal
        if 0 <= value_index < len(strings):
            value = strings[value_index]
            # Normalize variable names (ensure they start with --)
            if _re.match(r"^-[\w-]+$", value):
                value = _re.sub(r"^-+", "--", value)
            # Quote resource URLs for better formatting
            elif value and (
                value.startswith("project://") or value.startswith("resource://")
            ):
                value = f'"{value}"'
            return value
        return None

    elif value_type == 10:  # Variable name (should be wrapped in var())
        if 0 <= value_index < len(strings):
            varname = strings[value_index]
            # Normalize variable name
            varname = _re.sub(r"^-+", "--", varname)
            # Wrap in var() function
            return f"var({varname})"
        return None

    elif value_type == 11:  # Function call (already formatted)
        if 0 <= value_index < len(strings):
            return strings[value_index]
        return None

    return None


def _pick_best_value(
    prop_name: str,
    values: List[Tuple[int, int, str]],
    multi_value_shorthands: Dict[str, int],
    color_properties: set,
) -> Tuple[str, str]:
    """
    Pick the best value(s) for a property from multiple candidates.

    Args:
        prop_name: Property name
        values: List of (type, index, formatted_value) tuples
        multi_value_shorthands: Dict of multi-value property names
        color_properties: Set of color property names

    Returns:
        Tuple of (final_value, debug_comment)
    """
    if len(values) == 0:
        return ("", "")

    # For multi-value shorthands, combine valid values
    if prop_name in multi_value_shorthands:
        expected_count = multi_value_shorthands[prop_name]
        # Filter out invalid values
        valid_values = [
            (vtype, idx, val)
            for vtype, idx, val in values
            if not _is_invalid_value(val, prop_name, vtype, color_properties)
        ]

        if len(valid_values) > 0:
            # Take up to expected_count values
            selected = valid_values[:expected_count]
            combined = " ".join(val for _, _, val in selected)
            type_info = ", ".join(f"type={vtype}" for vtype, _, _ in selected)
            return (combined, type_info)

    # For single-value properties, pick the best value
    # Priority: Type 4 (color) > Type 11 (function) > Type 10 (var) > Type 3 (dimension) > Type 8 (string) > Type 2 (float)

    # Filter out invalid values first
    valid_values = [
        (vtype, idx, val)
        for vtype, idx, val in values
        if not _is_invalid_value(val, prop_name, vtype, color_properties)
    ]

    if len(valid_values) == 0:
        # All values are invalid, return the last one anyway
        vtype, idx, val = values[-1]
        return (val, f"type={vtype}, index={idx} (fallback)")

    # Pick best value based on priority
    if prop_name in color_properties:
        # For color properties, prefer color values
        color_vals = [(vt, vi, v) for vt, vi, v in valid_values if vt == 4]
        if color_vals:
            vtype, idx, val = color_vals[0]
            return (val, f"type={vtype}, color[{idx}]")

    # Priority order for non-color properties
    type_priority = {11: 0, 10: 1, 3: 2, 8: 3, 4: 4, 2: 5, 1: 6, 5: 7, 7: 8}

    sorted_values = sorted(valid_values, key=lambda x: type_priority.get(x[0], 99))
    vtype, idx, val = sorted_values[0]

    return (val, f"type={vtype}")


def _is_invalid_value(
    value: str, prop_name: str, value_type: int, color_properties: set
) -> bool:
    """
    Check if a value is invalid for the given property.

    Returns:
        True if the value should be skipped
    """
    # Skip obviously invalid values
    if value_type == 10 and ("absolute" in value or "invalid" in value):
        # Invalid variable references
        return True

    if value in ("absolute", "1.0px", "0.0px") and value_type in (2, 10):
        # These are likely parsing errors
        return True

    # Skip color values for non-color properties
    if prop_name not in color_properties and value_type == 4:
        return False  # Actually, colors might be valid in some contexts

    # Skip dimension values for color properties
    if prop_name in color_properties and value_type in (2, 3):
        return True

    return False


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

    selector_keys = ["m_Specificity", "m_Type", "m_PreviousRelationship", "ruleIndex"]
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

    if all(hasattr(obj, c) for c in ("r", "g", "b", "a")) and type(
        obj
    ).__name__.lower().startswith("color"):
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
