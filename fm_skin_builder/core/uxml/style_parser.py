"""
Style Parser - Unity StyleSheet → CSS Text

Converts Unity's compiled StyleSheet (USS) format into human-readable CSS text.
Handles colors, dimensions, variables, and all Unity StyleSheet value types.
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..logger import get_logger

log = get_logger(__name__)


class StyleParser:
    """Parses Unity StyleSheet objects into CSS text."""

    # Unity StyleSheet value types
    VALUE_TYPE_KEYWORD = 1  # Enum/keyword (e.g., "auto", "none")
    VALUE_TYPE_FLOAT = 2  # Float number
    VALUE_TYPE_DIMENSION = 3  # String dimension (e.g., "10px", "50%")
    VALUE_TYPE_COLOR = 4  # RGBA color
    VALUE_TYPE_RESOURCE = 5  # Resource path (e.g., url(...))
    VALUE_TYPE_ENUM = 7  # Enum value
    VALUE_TYPE_STRING = 8  # String value
    VALUE_TYPE_MISSING = 9  # Missing/unset value
    VALUE_TYPE_VARIABLE = 10  # CSS variable reference (e.g., var(--primary))

    def __init__(self):
        """Initialize the style parser."""
        pass

    def parse_stylesheet(self, stylesheet_data: Any) -> str:
        """
        Parse a Unity StyleSheet into CSS text.

        Args:
            stylesheet_data: Unity StyleSheet object from UnityPy

        Returns:
            CSS text representation
        """
        if not hasattr(stylesheet_data, "m_Rules"):
            log.warning("StyleSheet has no m_Rules attribute")
            return ""

        css_lines = []

        # Get data arrays
        strings = list(getattr(stylesheet_data, "strings", []))
        colors = list(getattr(stylesheet_data, "colors", []))
        rules = list(getattr(stylesheet_data, "m_Rules", []))

        # Get selectors
        selectors_by_rule = self._get_selectors_by_rule(stylesheet_data)

        # Parse each rule
        for rule_idx, rule in enumerate(rules):
            rule_selectors = selectors_by_rule.get(rule_idx, [])
            if not rule_selectors:
                # Skip rules without selectors
                continue

            properties = getattr(rule, "m_Properties", [])
            if not properties:
                continue

            # Build CSS rule
            selector_str = ", ".join(rule_selectors)
            css_lines.append(f"{selector_str} {{")

            # Parse each property
            for prop in properties:
                prop_name = getattr(prop, "m_Name", None)
                if not prop_name:
                    continue

                values = self._parse_property_values(
                    prop, strings, colors
                )

                if values:
                    value_str = ", ".join(values)
                    css_lines.append(f"  {prop_name}: {value_str};")

            css_lines.append("}")
            css_lines.append("")  # Empty line between rules

        return "\n".join(css_lines)

    def _get_selectors_by_rule(self, stylesheet_data: Any) -> Dict[int, List[str]]:
        """
        Extract selectors for each rule.

        Args:
            stylesheet_data: Unity StyleSheet object

        Returns:
            Dictionary mapping rule index to list of selector strings
        """
        selectors_by_rule: Dict[int, List[str]] = {}

        complex_selectors = getattr(stylesheet_data, "m_ComplexSelectors", [])

        for complex_sel in complex_selectors:
            rule_idx = getattr(complex_sel, "ruleIndex", -1)
            if rule_idx < 0:
                continue

            if rule_idx not in selectors_by_rule:
                selectors_by_rule[rule_idx] = []

            # Parse selector parts
            selectors = getattr(complex_sel, "m_Selectors", [])
            for selector in selectors:
                selector_str = self._parse_selector(selector)
                if selector_str and selector_str not in selectors_by_rule[rule_idx]:
                    selectors_by_rule[rule_idx].append(selector_str)

        return selectors_by_rule

    def _parse_selector(self, selector: Any) -> str:
        """
        Parse a Unity selector into CSS selector syntax.

        Args:
            selector: Unity selector object

        Returns:
            CSS selector string (e.g., ".button", "#my-id", "Label")
        """
        parts = getattr(selector, "m_Parts", [])
        if not parts:
            return ""

        selector_str = ""

        for part in parts:
            part_type = getattr(part, "m_Type", None)
            value = getattr(part, "m_Value", "")

            if part_type is None:
                continue

            # Type 0: Wildcard (*)
            if part_type == 0:
                selector_str += "*"

            # Type 1: Type selector (e.g., Label, Button)
            elif part_type == 1:
                selector_str += value

            # Type 2: Class selector (e.g., .button)
            elif part_type == 2:
                selector_str += f".{value}"

            # Type 3: ID selector (e.g., #my-id)
            elif part_type == 3:
                selector_str += f"#{value}"

            # Type 4: Descendant combinator ( )
            elif part_type == 4:
                selector_str += " "

            # Type 5: Child combinator (>)
            elif part_type == 5:
                selector_str += " > "

            # Type 6: Pseudo-class (e.g., :hover, :active)
            elif part_type == 6:
                selector_str += f":{value}"

        return selector_str.strip()

    def _parse_property_values(
        self,
        prop: Any,
        strings: List[str],
        colors: List[Any]
    ) -> List[str]:
        """
        Parse property values into CSS strings.

        Args:
            prop: Unity property object
            strings: String array from StyleSheet
            colors: Color array from StyleSheet

        Returns:
            List of CSS value strings
        """
        values = []

        for val in getattr(prop, "m_Values", []):
            value_type = getattr(val, "m_ValueType", None)
            value_index = getattr(val, "valueIndex", None)

            if value_type is None:
                continue

            # Parse based on value type
            if value_type == self.VALUE_TYPE_KEYWORD:
                # Keyword stored in strings
                if value_index is not None and 0 <= value_index < len(strings):
                    values.append(strings[value_index])

            elif value_type == self.VALUE_TYPE_FLOAT:
                # Float value stored directly
                float_val = getattr(val, "value", 0.0)
                values.append(str(float_val))

            elif value_type == self.VALUE_TYPE_DIMENSION:
                # Dimension stored as string
                if value_index is not None and 0 <= value_index < len(strings):
                    values.append(strings[value_index])

            elif value_type == self.VALUE_TYPE_COLOR:
                # Color stored in colors array
                if value_index is not None and 0 <= value_index < len(colors):
                    color_obj = colors[value_index]
                    hex_color = self._color_to_hex(color_obj)
                    values.append(hex_color)

            elif value_type == self.VALUE_TYPE_RESOURCE:
                # Resource path stored in strings
                if value_index is not None and 0 <= value_index < len(strings):
                    resource_path = strings[value_index]
                    values.append(f"url({resource_path})")

            elif value_type == self.VALUE_TYPE_STRING:
                # String value
                if value_index is not None and 0 <= value_index < len(strings):
                    string_val = strings[value_index]
                    # Quote if necessary
                    if " " in string_val or "," in string_val:
                        values.append(f'"{string_val}"')
                    else:
                        values.append(string_val)

            elif value_type == self.VALUE_TYPE_VARIABLE:
                # CSS variable reference
                if value_index is not None and 0 <= value_index < len(strings):
                    var_name = strings[value_index]
                    # Ensure it starts with --
                    if not var_name.startswith("--"):
                        var_name = f"--{var_name}"
                    values.append(f"var({var_name})")

            elif value_type == self.VALUE_TYPE_MISSING:
                # Missing/unset value
                values.append("initial")

        return values

    def _color_to_hex(self, color_obj: Any) -> str:
        """
        Convert Unity color to hex string.

        Args:
            color_obj: Unity color object with r, g, b, a fields

        Returns:
            Hex color string (e.g., "#1976d2" or "#1976d2ff" with alpha)
        """
        r = int(getattr(color_obj, "r", 0.0) * 255)
        g = int(getattr(color_obj, "g", 0.0) * 255)
        b = int(getattr(color_obj, "b", 0.0) * 255)
        a = int(getattr(color_obj, "a", 1.0) * 255)

        # Include alpha if not fully opaque
        if a < 255:
            return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
        else:
            return f"#{r:02x}{g:02x}{b:02x}"

    def parse_inline_styles(self, element_data: Any, strings: List[str], colors: List[Any]) -> str:
        """
        Parse inline styles from a VisualElement.

        Args:
            element_data: Unity VisualElement asset data
            strings: String array from parent UXML
            colors: Color array from parent UXML

        Returns:
            CSS inline style string
        """
        # Check if element has inline style properties
        if not hasattr(element_data, "m_StyleValues"):
            return ""

        style_values = getattr(element_data, "m_StyleValues", None)
        if not style_values:
            return ""

        # Parse style properties
        # Note: This is a simplified version. Unity's inline styles are complex.
        # Full implementation would need to handle all style property types.

        properties = []

        # This would need to be expanded based on Unity's actual structure
        # For now, return empty - inline styles are typically in a separate StyleSheet

        return "; ".join(properties)
