"""
CSS Extractor

Extracts CSS variables and classes from Unity StyleSheet (USS) assets.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import UnityPy
import re

from .base import BaseAssetExtractor
from ..models import CSSVariable, CSSClass, CSSProperty, CSSValueDefinition
from ...css_utils import build_selector_from_parts


class CSSExtractor(BaseAssetExtractor):
    """Extracts CSS variables and classes from StyleSheet assets."""

    def extract_from_bundle(self, bundle_path: Path) -> Dict[str, List[Any]]:
        """
        Extract CSS variables and classes from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            Dictionary with 'variables' and 'classes' lists
        """
        import gc

        variables: List[CSSVariable] = []
        classes: List[CSSClass] = []

        try:
            env = UnityPy.load(str(bundle_path))
        except Exception as e:
            # If we can't load the bundle, return empty results
            return {"variables": variables, "classes": classes}

        bundle_name = bundle_path.name

        try:
            for obj in env.objects:
                if obj.type.name != "MonoBehaviour":
                    continue

                try:
                    data = obj.read()
                except Exception:
                    continue

                # Check if this is a StyleSheet asset
                if not hasattr(data, "colors") or not hasattr(data, "strings"):
                    continue

                stylesheet_name = self._get_asset_name(data) or "UnnamedStyleSheet"
                strings = list(getattr(data, "strings", []))
                colors = getattr(data, "colors", [])
                rules = getattr(data, "m_Rules", [])
                rule_selectors = self._get_rule_selectors(data)

                # Extract CSS variables and classes from each rule
                for rule_idx, rule in enumerate(rules):
                    selectors = rule_selectors.get(rule_idx, [])
                    properties = getattr(rule, "m_Properties", [])

                    for prop in properties:
                        prop_name = getattr(prop, "m_Name", None)
                        if not prop_name:
                            continue

                        # Parse values
                        value_defs = self._extract_values(
                            prop, strings, colors
                        )

                        # Check if this property defines a CSS variable
                        if prop_name and prop_name.startswith("--"):
                            # This is a CSS variable definition
                            css_var = self._create_css_variable(
                                name=prop_name,
                                stylesheet=stylesheet_name,
                                bundle=bundle_name,
                                rule_index=rule_idx,
                                values=value_defs,
                            )
                            if css_var:
                                variables.append(css_var)

                    # Create CSS class entries for non-variable selectors
                    if selectors and properties:
                        for selector in selectors:
                            if not selector.startswith("--"):  # Skip variable selectors
                                css_class = self._create_css_class(
                                    name=selector,
                                    stylesheet=stylesheet_name,
                                    bundle=bundle_name,
                                    properties=properties,
                                    strings=strings,
                                    colors=colors,
                                )
                                if css_class:
                                    classes.append(css_class)
        finally:
            # Clean up UnityPy environment
            try:
                del env
            except:
                pass
            gc.collect()

        return {"variables": variables, "classes": classes}

    def _get_rule_selectors(self, data: Any) -> Dict[int, List[str]]:
        """
        Extract selectors for each rule.

        Args:
            data: StyleSheet data

        Returns:
            Dictionary mapping rule index to list of selector strings
        """
        rules = getattr(data, "m_Rules", [])
        selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
            data, "m_ComplexSelectors"
        ) else []

        out: Dict[int, List[str]] = {i: [] for i in range(len(rules))}

        for sel in selectors:
            rule_idx = getattr(sel, "ruleIndex", -1)
            if 0 <= rule_idx < len(rules):
                for s in getattr(sel, "m_Selectors", []) or []:
                    parts = getattr(s, "m_Parts", [])
                    selector_str = build_selector_from_parts(parts)
                    if selector_str:
                        out[rule_idx].append(selector_str)

        return out

    def _extract_values(
        self, prop: Any, strings: List[str], colors: List[Any]
    ) -> List[CSSValueDefinition]:
        """
        Extract value definitions from a property.

        Args:
            prop: Property object
            strings: String array
            colors: Color array

        Returns:
            List of CSSValueDefinition objects
        """
        value_defs = []

        for val in getattr(prop, "m_Values", []):
            value_type = getattr(val, "m_ValueType", None)
            value_index = getattr(val, "valueIndex", None)

            if value_type is None or value_index is None:
                continue

            resolved_value = ""
            raw_value = None

            # Type 3: Dimension (e.g., "10px")
            # Type 8: String
            # Type 10: Variable reference (e.g., "var(--primary)")
            if value_type in (3, 8, 10):
                if isinstance(value_index, int) and 0 <= value_index < len(strings):
                    resolved_value = str(strings[value_index])

            # Type 4: Color
            elif value_type == 4:
                if isinstance(value_index, int) and 0 <= value_index < len(colors):
                    color_obj = colors[value_index]
                    r = getattr(color_obj, "r", 0.0)
                    g = getattr(color_obj, "g", 0.0)
                    b = getattr(color_obj, "b", 0.0)
                    a = getattr(color_obj, "a", 1.0)

                    # Convert to hex
                    resolved_value = self._rgba_to_hex(r, g, b, a)
                    raw_value = {"r": r, "g": g, "b": b, "a": a}

            value_def = CSSValueDefinition(
                value_type=value_type,
                index=value_index,
                resolved_value=resolved_value or f"<unknown-type-{value_type}>",
                raw_value=raw_value,
            )
            value_defs.append(value_def)

        return value_defs

    def _create_css_variable(
        self,
        name: str,
        stylesheet: str,
        bundle: str,
        rule_index: int,
        values: List[CSSValueDefinition],
    ) -> CSSVariable | None:
        """Create a CSSVariable model instance."""
        if not values:
            return None

        # Extract colors from values
        colors = []
        string_index = None
        color_index = None

        for val in values:
            if val.value_type == 4 and val.resolved_value.startswith("#"):
                colors.append(val.resolved_value)
                if color_index is None:
                    color_index = val.index
            elif val.value_type in (3, 8, 10):
                if string_index is None:
                    string_index = val.index

        return CSSVariable(
            name=name,
            stylesheet=stylesheet,
            bundle=bundle,
            property_name=name,  # For variables, property_name == name
            rule_index=rule_index,
            values=values,
            string_index=string_index,
            color_index=color_index,
            colors=colors,
            **self._create_default_status(),
        )

    def _create_css_class(
        self,
        name: str,
        stylesheet: str,
        bundle: str,
        properties: List[Any],
        strings: List[str],
        colors: List[Any],
    ) -> CSSClass | None:
        """Create a CSSClass model instance."""
        if not properties:
            return None

        css_properties = []
        variables_used = set()

        for prop in properties:
            prop_name = getattr(prop, "m_Name", None)
            if not prop_name:
                continue

            value_defs = self._extract_values(prop, strings, colors)

            # Track variable references
            for val in value_defs:
                if val.value_type == 10:  # Variable reference
                    variables_used.add(val.resolved_value)

            css_prop = CSSProperty(name=prop_name, values=value_defs)
            css_properties.append(css_prop)

        # Generate tags from class name
        tags = self._generate_tags_from_selector(name)

        return CSSClass(
            name=name,
            stylesheet=stylesheet,
            bundle=bundle,
            properties=css_properties,
            variables_used=sorted(list(variables_used)),
            tags=tags,
            **self._create_default_status(),
        )

    def _rgba_to_hex(self, r: float, g: float, b: float, a: float) -> str:
        """
        Convert RGBA (0.0-1.0) to hex color.

        Args:
            r, g, b, a: Color components (0.0-1.0)

        Returns:
            Hex color string (e.g., "#1976d2" or "#1976d2ff" with alpha)
        """
        r_int = int(r * 255)
        g_int = int(g * 255)
        b_int = int(b * 255)

        if a < 1.0:
            a_int = int(a * 255)
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}{a_int:02x}"
        else:
            return f"#{r_int:02x}{g_int:02x}{b_int:02x}"

    def _generate_tags_from_selector(self, selector: str) -> List[str]:
        """
        Generate tags from CSS selector.

        Args:
            selector: CSS selector (e.g., ".button-primary")

        Returns:
            List of tags
        """
        tags = []

        # Remove leading . or #
        clean = selector.lstrip(".#")

        # Split by - or _
        parts = re.split(r'[-_]', clean)

        for part in parts:
            if len(part) > 2:  # Skip very short parts
                tags.append(part.lower())

        return tags
