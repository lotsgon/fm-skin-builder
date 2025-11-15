"""
CSS/USS Property Resolver

Resolves CSS variable references, extracts tokens, and builds comprehensive
property introspection data for the asset catalogue.
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Optional, Any
import re

from ..logger import get_logger

log = get_logger(__name__)

# Patterns for token extraction
HEX_COLOR_PATTERN = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})")
RGBA_PATTERN = re.compile(r"rgba?\([^)]+\)")
VAR_REFERENCE_PATTERN = re.compile(r"var\((--[\w-]+)\)")
SPRITE_REFERENCE_PATTERN = re.compile(
    r"(?:url\(['\"]?|sprite://|resource://)([^'\")\s]+)"
)
NUMERIC_TOKEN_PATTERN = re.compile(r"\d+(?:\.\d+)?(?:px|%|em|rem)")


class CSSResolver:
    """
    Resolves CSS variable references and extracts tokens from properties.
    """

    def __init__(self, css_variables: Optional[Dict[str, str]] = None):
        """
        Initialize CSS resolver.

        Args:
            css_variables: Dictionary mapping variable names to resolved values
                          e.g., {'--primary-color': '#1976d2'}
        """
        self.css_variables = css_variables or {}
        self._resolution_cache: Dict[str, str] = {}

    def resolve_property_value(
        self, value: str, max_depth: int = 10
    ) -> Tuple[str, Set[str]]:
        """
        Resolve CSS variable references in a property value.

        Args:
            value: CSS property value (may contain var() references)
            max_depth: Maximum resolution depth (prevents infinite loops)

        Returns:
            Tuple of (resolved_value, set_of_variables_used)
        """
        if not value or max_depth <= 0:
            return value, set()

        # Check cache
        if value in self._resolution_cache:
            # Still need to extract variables for tracking
            variables_used = self.extract_variable_references(value)
            return self._resolution_cache[value], variables_used

        variables_used = set()
        resolved = value

        # Find all var() references
        matches = list(VAR_REFERENCE_PATTERN.finditer(resolved))

        # Resolve each variable reference
        for match in reversed(matches):  # Reverse to preserve string positions
            var_name = match.group(1)
            variables_used.add(var_name)

            # Look up variable value
            var_value = self.css_variables.get(var_name)

            if var_value:
                # Recursively resolve if the variable value contains more variables
                if "var(" in var_value:
                    var_value, nested_vars = self.resolve_property_value(
                        var_value, max_depth - 1
                    )
                    variables_used.update(nested_vars)

                # Replace the var() reference
                resolved = resolved[: match.start()] + var_value + resolved[match.end() :]
            else:
                log.debug(f"Variable {var_name} not found in variable registry")

        # Cache result
        self._resolution_cache[value] = resolved

        return resolved, variables_used

    def extract_variable_references(self, value: str) -> Set[str]:
        """
        Extract all CSS variable references from a value.

        Args:
            value: CSS property value

        Returns:
            Set of variable names (e.g., {'--primary-color', '--button-bg'})
        """
        if not value:
            return set()

        matches = VAR_REFERENCE_PATTERN.findall(value)
        return set(matches)

    def extract_color_tokens(self, value: str) -> List[str]:
        """
        Extract all color tokens (hex/rgba) from a value.

        Args:
            value: CSS property value

        Returns:
            List of color tokens normalized to uppercase hex
        """
        if not value:
            return []

        colors = []

        # Extract hex colors
        hex_matches = HEX_COLOR_PATTERN.findall(value)
        for hex_color in hex_matches:
            colors.append(f"#{hex_color.upper()}")

        # Extract rgba colors (keep as-is for now)
        rgba_matches = RGBA_PATTERN.findall(value)
        colors.extend(rgba_matches)

        return colors

    def extract_numeric_tokens(self, value: str) -> List[str]:
        """
        Extract numeric tokens (px, %, em, rem) from a value.

        Args:
            value: CSS property value

        Returns:
            List of numeric tokens (e.g., ['4px', '50%'])
        """
        if not value:
            return []

        matches = NUMERIC_TOKEN_PATTERN.findall(value)
        return matches

    def extract_asset_references(self, value: str) -> List[str]:
        """
        Extract asset references (sprites, textures) from a value.

        Args:
            value: CSS property value

        Returns:
            List of asset references (e.g., ['FMImages_1x/star_full'])
        """
        if not value:
            return []

        matches = SPRITE_REFERENCE_PATTERN.findall(value)

        # Clean up asset paths
        cleaned = []
        for match in matches:
            # Remove common prefixes
            path = match.replace("resource://", "").replace("sprite://", "")
            # Remove quotes
            path = path.strip("\"'")
            if path:
                cleaned.append(path)

        return cleaned

    def build_property_summary(
        self, properties: Dict[str, str], resolved_properties: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Build a property summary for quick overview.

        Args:
            properties: Raw property dictionary
            resolved_properties: Resolved property dictionary

        Returns:
            Summary dictionary with colors, assets, variables, and layout
        """
        summary: Dict[str, Any] = {
            "colors": [],
            "assets": [],
            "variables": [],
            "layout": {},
        }

        all_colors = set()
        all_assets = set()
        all_variables = set()

        # Extract from all properties
        for prop_name, prop_value in properties.items():
            # Extract variables
            variables = self.extract_variable_references(prop_value)
            all_variables.update(variables)

            # Extract assets
            assets = self.extract_asset_references(prop_value)
            all_assets.update(assets)

        # Extract colors from resolved properties
        for prop_name, resolved_value in resolved_properties.items():
            colors = self.extract_color_tokens(resolved_value)
            all_colors.update(colors)

            # Build layout summary for relevant properties
            if prop_name in [
                "padding",
                "margin",
                "border-radius",
                "width",
                "height",
                "display",
                "position",
            ]:
                summary["layout"][prop_name] = resolved_value

        summary["colors"] = sorted(list(all_colors))
        summary["assets"] = sorted(list(all_assets))
        summary["variables"] = sorted(list(all_variables))

        return summary

    def build_variable_registry(
        self, css_variables: List[Any]
    ) -> Dict[str, str]:
        """
        Build a variable registry from CSSVariable objects.

        Args:
            css_variables: List of CSSVariable model instances

        Returns:
            Dictionary mapping variable names to resolved values
        """
        registry = {}

        for var in css_variables:
            name = var.name if hasattr(var, "name") else var.get("name")
            values = var.values if hasattr(var, "values") else var.get("values", [])

            if not name or not values:
                continue

            # Get the first resolved value (most CSS variables have a single value)
            resolved_value = None
            if isinstance(values, list) and len(values) > 0:
                first_value = values[0]
                if hasattr(first_value, "resolved_value"):
                    resolved_value = first_value.resolved_value
                elif isinstance(first_value, dict):
                    resolved_value = first_value.get("resolved_value")

            if resolved_value:
                registry[name] = resolved_value

        log.debug(f"Built variable registry with {len(registry)} variables")
        return registry


def resolve_css_class_properties(
    css_class: Any,
    css_variables: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str], List[str], List[str], List[str], List[str]]:
    """
    Resolve all properties of a CSS class, extracting comprehensive data.

    Args:
        css_class: CSSClass model instance or dict
        css_variables: Variable registry (name -> resolved value)

    Returns:
        Tuple of:
        - raw_properties: Dict mapping property name to raw value
        - resolved_properties: Dict mapping property name to resolved value
        - variables_used: List of unique variable names used
        - color_tokens: List of unique color tokens
        - numeric_tokens: List of unique numeric tokens
        - asset_dependencies: List of unique asset references
    """
    resolver = CSSResolver(css_variables)

    raw_properties = {}
    resolved_properties = {}
    all_variables = set()
    all_colors = set()
    all_numerics = set()
    all_assets = set()

    # Get properties list
    properties = css_class.properties if hasattr(css_class, "properties") else css_class.get("properties", [])

    for prop in properties:
        prop_name = prop.name if hasattr(prop, "name") else prop.get("name")
        values = prop.values if hasattr(prop, "values") else prop.get("values", [])

        if not prop_name:
            continue

        # Build raw value string
        raw_value_parts = []
        for val in values:
            resolved = val.resolved_value if hasattr(val, "resolved_value") else val.get("resolved_value", "")
            if resolved:
                raw_value_parts.append(resolved)

        raw_value = ", ".join(raw_value_parts)
        raw_properties[prop_name] = raw_value

        # Resolve variables
        resolved_value, variables = resolver.resolve_property_value(raw_value)
        resolved_properties[prop_name] = resolved_value
        all_variables.update(variables)

        # Extract colors from resolved value
        colors = resolver.extract_color_tokens(resolved_value)
        all_colors.update(colors)

        # Extract numeric tokens
        numerics = resolver.extract_numeric_tokens(resolved_value)
        all_numerics.update(numerics)

        # Extract asset references
        assets = resolver.extract_asset_references(raw_value)
        all_assets.update(assets)

    return (
        raw_properties,
        resolved_properties,
        sorted(list(all_variables)),
        sorted(list(all_colors)),
        sorted(list(all_numerics)),
        sorted(list(all_assets)),
    )
