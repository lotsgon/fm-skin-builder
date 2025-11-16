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
from ..models import CSSVariable, CSSClass, CSSValueDefinition
from ...css_utils import build_selector_from_parts, format_property_value, _format_uss_value
from ..css_resolver import CSSResolver, resolve_css_class_properties


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
        except Exception:
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
                floats = getattr(data, "floats", []) if hasattr(data, "floats") else []
                dimensions = getattr(data, "dimensions", []) if hasattr(data, "dimensions") else []
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

                        # Check if this property defines a CSS variable
                        if prop_name and prop_name.startswith("--"):
                            # This is a CSS variable definition
                            css_var = self._create_css_variable(
                                name=prop_name,
                                stylesheet=stylesheet_name,
                                bundle=bundle_name,
                                prop=prop,
                                strings=strings,
                                colors_array=colors,
                                floats=floats,
                                dimensions=dimensions,
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
                                    floats=floats,
                                    dimensions=dimensions,
                                )
                                if css_class:
                                    classes.append(css_class)

            # Build variable registry and enhance classes with resolution
            if variables and classes:
                resolver = CSSResolver()
                var_registry = resolver.build_variable_registry(variables)
                self._enhance_classes_with_resolution(classes, var_registry)

        finally:
            # Clean up UnityPy environment
            try:
                del env
            except Exception:
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
        selectors = (
            getattr(data, "m_ComplexSelectors", [])
            if hasattr(data, "m_ComplexSelectors")
            else []
        )

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
        self,
        prop: Any,
        strings: List[str],
        colors: List[Any],
        floats: List[float],
        dimensions: List[Any],
    ) -> List[CSSValueDefinition]:
        """
        Extract value definitions from a property.

        Uses the same USS formatting logic as the patch workflow to ensure
        consistent value representation across the codebase.

        Args:
            prop: Property object
            strings: String array
            colors: Color array
            floats: Floats array
            dimensions: Dimensions array

        Returns:
            List of CSSValueDefinition objects with properly formatted USS values
        """
        value_defs = []
        prop_name = getattr(prop, "m_Name", "")

        for val in getattr(prop, "m_Values", []):
            value_type = getattr(val, "m_ValueType", None)
            value_index = getattr(val, "valueIndex", None)

            if value_type is None or value_index is None:
                continue

            # Use the SAME USS formatting logic as the patch workflow
            # This ensures consistent value representation across the codebase
            resolved_value = _format_uss_value(
                value_type=value_type,
                value_index=value_index,
                strings=strings,
                colors=colors,
                floats=floats,
                dimensions=dimensions,
                prop_name=prop_name,
            )

            # Store raw color data for color values (for backward compatibility)
            raw_value = None
            if value_type == 4 and isinstance(value_index, int) and 0 <= value_index < len(colors):
                color_obj = colors[value_index]
                raw_value = {
                    "r": getattr(color_obj, "r", 0.0),
                    "g": getattr(color_obj, "g", 0.0),
                    "b": getattr(color_obj, "b", 0.0),
                    "a": getattr(color_obj, "a", 1.0),
                }

            value_def = CSSValueDefinition(
                value_type=value_type,
                index=value_index,
                resolved_value=resolved_value or f"<type-{value_type}>",
                raw_value=raw_value,
            )
            value_defs.append(value_def)

        return value_defs

    def _create_css_variable(
        self,
        name: str,
        stylesheet: str,
        bundle: str,
        prop: Any,
        strings: List[str],
        colors_array: List[Any],
        floats: List[float],
        dimensions: List[Any],
    ) -> CSSVariable | None:
        """Create a CSSVariable model instance."""
        # Get the actual CSS/USS text value using format_property_value()
        css_text_value = format_property_value(
            prop,
            strings,
            colors_array,
            floats,
            dimensions,
        )

        if not css_text_value:
            return None

        # Extract colors from the value for search indexing
        colors = []
        # Match hex colors in the value
        hex_matches = re.findall(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?", css_text_value)
        colors.extend(hex_matches)

        # Also match rgba() colors and convert to hex if needed
        rgba_matches = re.findall(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)", css_text_value)
        for r, g, b in rgba_matches:
            hex_color = f"#{int(r):02X}{int(g):02X}{int(b):02X}"
            if hex_color not in colors:
                colors.append(hex_color)

        return CSSVariable(
            name=name,
            value=css_text_value,
            stylesheet=stylesheet,
            bundle=bundle,
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
        floats: List[float],
        dimensions: List[Any],
    ) -> CSSClass | None:
        """Create a CSSClass model instance."""
        if not properties:
            return None

        variables_used = set()
        raw_properties = {}  # Store actual CSS/USS text values

        for prop in properties:
            prop_name = getattr(prop, "m_Name", None)
            if not prop_name:
                continue

            # Get the actual CSS/USS text value using the SAME logic as patch workflow
            # This reuses format_property_value() which extracts logic from serialize_stylesheet_to_uss()
            css_text_value = format_property_value(
                prop,
                strings,
                colors,
                floats,
                dimensions,
            )

            # Store the actual CSS/USS text value
            if css_text_value:
                raw_properties[prop_name] = css_text_value

            # Track variable references from the CSS text
            if "var(--" in css_text_value:
                # Extract variable names from var() references
                var_matches = re.findall(r"var\((--[\w-]+)\)", css_text_value)
                variables_used.update(var_matches)

        # Generate tags from class name
        tags = self._generate_tags_from_selector(name)

        return CSSClass(
            name=name,
            stylesheet=stylesheet,
            bundle=bundle,
            raw_properties=raw_properties,  # Store actual CSS/USS text
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
        parts = re.split(r"[-_]", clean)

        for part in parts:
            if len(part) > 2:  # Skip very short parts
                tags.append(part.lower())

        return tags

    def _enhance_classes_with_resolution(
        self, classes: List[CSSClass], var_registry: Dict[str, str]
    ) -> None:
        """
        Enhance CSS classes with resolved properties and comprehensive data.

        Args:
            classes: List of CSSClass instances to enhance
            var_registry: Variable registry mapping names to resolved values
        """
        for css_class in classes:
            try:
                # Resolve properties and extract comprehensive data
                (
                    old_raw_properties,
                    variables_used,
                    color_tokens,
                    numeric_tokens,
                    asset_dependencies,
                ) = resolve_css_class_properties(css_class, var_registry)

                # Update class with enhanced data
                # raw_properties was already set correctly during _create_css_class()
                css_class.variables_used = variables_used
                css_class.color_tokens = color_tokens
                css_class.numeric_tokens = numeric_tokens
                css_class.asset_dependencies = asset_dependencies

            except Exception as e:
                # Log error but don't fail the entire extraction
                from ...logger import get_logger
                log = get_logger(__name__)
                log.warning(
                    f"Failed to enhance class {css_class.name}: {e}"
                )
