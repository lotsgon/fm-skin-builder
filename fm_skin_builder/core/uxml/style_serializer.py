"""
Style Serializer - CSS Text → Unity StyleSheet

Converts CSS text into Unity's compiled StyleSheet (USS) format.
Handles the reverse of StyleParser: parsing CSS and building Unity structures.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple
from ..logger import get_logger

log = get_logger(__name__)


class StyleSerializer:
    """Serializes CSS text into Unity StyleSheet structures."""

    # Unity StyleSheet value types (same as StyleParser)
    VALUE_TYPE_KEYWORD = 1
    VALUE_TYPE_FLOAT = 2
    VALUE_TYPE_DIMENSION = 3
    VALUE_TYPE_COLOR = 4
    VALUE_TYPE_RESOURCE = 5
    VALUE_TYPE_ENUM = 7
    VALUE_TYPE_STRING = 8
    VALUE_TYPE_MISSING = 9
    VALUE_TYPE_VARIABLE = 10

    def __init__(self):
        """Initialize the style serializer."""
        pass

    def parse_css(self, css_text: str) -> List[Dict[str, Any]]:
        """
        Parse CSS text into rule structures.

        Args:
            css_text: CSS text to parse

        Returns:
            List of rule dictionaries with 'selector' and 'properties'
        """
        rules = []

        # Remove comments
        css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

        # Match rules: selector { property: value; ... }
        rule_pattern = r"([^{]+)\{([^}]+)\}"

        for match in re.finditer(rule_pattern, css_text):
            selector_text = match.group(1).strip()
            properties_text = match.group(2).strip()

            # Parse selectors (can be comma-separated)
            selectors = [s.strip() for s in selector_text.split(",")]

            # Parse properties
            properties = self._parse_properties(properties_text)

            for selector in selectors:
                if selector and properties:
                    rules.append({"selector": selector, "properties": properties})

        return rules

    def _parse_properties(self, properties_text: str) -> Dict[str, List[str]]:
        """
        Parse CSS properties from text.

        Args:
            properties_text: CSS property declarations

        Returns:
            Dictionary mapping property names to lists of values
        """
        properties = {}

        # Split by semicolon
        for decl in properties_text.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue

            # Split property and value
            parts = decl.split(":", 1)
            if len(parts) != 2:
                continue

            prop_name = parts[0].strip()
            prop_value = parts[1].strip()

            # Split multi-value properties by comma
            values = [v.strip() for v in prop_value.split(",")]

            properties[prop_name] = values

        return properties

    def build_stylesheet_data(
        self, rules: List[Dict[str, Any]], base_stylesheet: Optional[Any] = None
    ) -> Tuple[List[str], List[Any], List[Any], List[Any]]:
        """
        Build Unity StyleSheet data structures from parsed rules.

        Args:
            rules: List of rule dictionaries from parse_css()
            base_stylesheet: Optional existing StyleSheet to extend

        Returns:
            Tuple of (strings, colors, unity_rules, complex_selectors)
        """
        strings = []
        colors = []
        string_map = {}  # Map string -> index
        color_map = {}  # Map color tuple -> index

        # If we have a base stylesheet, preserve its data
        if base_stylesheet:
            strings = list(getattr(base_stylesheet, "strings", []))
            colors = list(getattr(base_stylesheet, "colors", []))

            # Build maps for deduplication
            for i, s in enumerate(strings):
                string_map[s] = i

            for i, c in enumerate(colors):
                color_tuple = (c.r, c.g, c.b, c.a)
                color_map[color_tuple] = i

        unity_rules = []
        complex_selectors = []

        for rule_idx, rule in enumerate(rules):
            selector = rule["selector"]
            properties_dict = rule["properties"]

            # Build Unity property objects
            unity_properties = []

            for prop_name, values in properties_dict.items():
                # Build Unity property structure
                unity_values = []

                for value_str in values:
                    value_type, value_index, value_data = self._serialize_value(
                        value_str, strings, colors, string_map, color_map
                    )

                    unity_values.append(
                        {
                            "m_ValueType": value_type,
                            "valueIndex": value_index,
                            "value": value_data,
                        }
                    )

                unity_properties.append({"m_Name": prop_name, "m_Values": unity_values})

            # Build Unity rule
            unity_rules.append({"m_Properties": unity_properties})

            # Build complex selector
            selector_parts = self._parse_selector(selector)
            complex_selectors.append(
                {"ruleIndex": rule_idx, "m_Selectors": [{"m_Parts": selector_parts}]}
            )

        return strings, colors, unity_rules, complex_selectors

    def _serialize_value(
        self,
        value_str: str,
        strings: List[str],
        colors: List[Any],
        string_map: Dict[str, int],
        color_map: Dict[Tuple[float, float, float, float], int],
    ) -> Tuple[int, int, Any]:
        """
        Serialize a CSS value into Unity format.

        Args:
            value_str: CSS value string
            strings: String array (will be modified)
            colors: Color array (will be modified)
            string_map: Map of strings to indices
            color_map: Map of color tuples to indices

        Returns:
            Tuple of (value_type, value_index, value_data)
        """
        value_str = value_str.strip()

        # Check for CSS variable
        if value_str.startswith("var(") and value_str.endswith(")"):
            var_name = value_str[4:-1].strip()
            # Ensure -- prefix
            if not var_name.startswith("--"):
                var_name = f"--{var_name}"

            # Add to strings
            if var_name not in string_map:
                string_map[var_name] = len(strings)
                strings.append(var_name)

            return (self.VALUE_TYPE_VARIABLE, string_map[var_name], None)

        # Check for color (hex format)
        if value_str.startswith("#"):
            color_tuple = self._parse_hex_color(value_str)
            if color_tuple:
                # Add to colors
                if color_tuple not in color_map:
                    # Create Unity color object (dict representation)
                    color_obj = {
                        "r": color_tuple[0],
                        "g": color_tuple[1],
                        "b": color_tuple[2],
                        "a": color_tuple[3],
                    }
                    color_map[color_tuple] = len(colors)
                    colors.append(color_obj)

                return (self.VALUE_TYPE_COLOR, color_map[color_tuple], None)

        # Check for resource path
        if value_str.startswith("url(") and value_str.endswith(")"):
            resource_path = value_str[4:-1].strip().strip('"').strip("'")

            # Add to strings
            if resource_path not in string_map:
                string_map[resource_path] = len(strings)
                strings.append(resource_path)

            return (self.VALUE_TYPE_RESOURCE, string_map[resource_path], None)

        # Check for float
        try:
            float_val = float(value_str)
            return (
                self.VALUE_TYPE_FLOAT,
                0,  # Float values don't use index
                float_val,
            )
        except ValueError:
            pass

        # Check for dimension (e.g., "10px", "50%")
        if re.match(r"^-?\d+\.?\d*(px|%|em|rem|vh|vw)$", value_str):
            # Add to strings
            if value_str not in string_map:
                string_map[value_str] = len(strings)
                strings.append(value_str)

            return (self.VALUE_TYPE_DIMENSION, string_map[value_str], None)

        # Default: treat as keyword or string
        # Add to strings
        if value_str not in string_map:
            string_map[value_str] = len(strings)
            strings.append(value_str)

        return (self.VALUE_TYPE_KEYWORD, string_map[value_str], None)

    def _parse_hex_color(
        self, hex_str: str
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Parse hex color string to RGBA tuple.

        Args:
            hex_str: Hex color string (e.g., "#1976d2" or "#1976d2ff")

        Returns:
            Tuple of (r, g, b, a) as floats 0.0-1.0, or None if invalid
        """
        hex_str = hex_str.lstrip("#")

        try:
            if len(hex_str) == 6:
                # RGB
                r = int(hex_str[0:2], 16) / 255.0
                g = int(hex_str[2:4], 16) / 255.0
                b = int(hex_str[4:6], 16) / 255.0
                a = 1.0
            elif len(hex_str) == 8:
                # RGBA
                r = int(hex_str[0:2], 16) / 255.0
                g = int(hex_str[2:4], 16) / 255.0
                b = int(hex_str[4:6], 16) / 255.0
                a = int(hex_str[6:8], 16) / 255.0
            else:
                return None

            return (r, g, b, a)

        except ValueError:
            return None

    def _parse_selector(self, selector_str: str) -> List[Dict[str, Any]]:
        """
        Parse CSS selector into Unity selector parts.

        Args:
            selector_str: CSS selector string (e.g., ".button", "#my-id", "Label")

        Returns:
            List of selector part dictionaries
        """
        parts = []

        # Simple parser for basic selectors
        # Full implementation would need proper CSS selector parsing

        # Split by combinators
        tokens = re.split(r"(\s+|>)", selector_str)

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Descendant combinator
            if token == " " or token.isspace():
                parts.append(
                    {
                        "m_Type": 4,  # Descendant
                        "m_Value": "",
                    }
                )

            # Child combinator
            elif token == ">":
                parts.append(
                    {
                        "m_Type": 5,  # Child
                        "m_Value": "",
                    }
                )

            # Class selector
            elif token.startswith("."):
                parts.append(
                    {
                        "m_Type": 2,  # Class
                        "m_Value": token[1:],
                    }
                )

            # ID selector
            elif token.startswith("#"):
                parts.append(
                    {
                        "m_Type": 3,  # ID
                        "m_Value": token[1:],
                    }
                )

            # Pseudo-class
            elif token.startswith(":"):
                parts.append(
                    {
                        "m_Type": 6,  # Pseudo-class
                        "m_Value": token[1:],
                    }
                )

            # Wildcard
            elif token == "*":
                parts.append(
                    {
                        "m_Type": 0,  # Wildcard
                        "m_Value": "",
                    }
                )

            # Type selector
            else:
                parts.append(
                    {
                        "m_Type": 1,  # Type
                        "m_Value": token,
                    }
                )

        return parts
