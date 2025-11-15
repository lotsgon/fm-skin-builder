"""
Property handlers for applying CSS values to Unity StyleSheets.

This module contains logic for applying different types of CSS properties
to Unity StyleSheet assets, handling the various value types (floats, colors,
keywords, resources, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .logger import get_logger
from .value_parsers import (
    parse_float_value,
    parse_keyword_value,
    parse_resource_value,
    FloatValue,
    KeywordValue,
    ResourceValue,
)
from .css_utils import normalize_css_color

log = get_logger(__name__)

__all__ = [
    "PropertyType",
    "PropertyHandler",
    "get_property_handler",
    "apply_property_value",
]


@dataclass
class PropertyType:
    """
    Defines the expected type(s) for a USS property.
    """

    name: str
    unity_types: List[
        int
    ]  # Unity StyleSheet value types (1=keyword, 2=float, 4=color, 7=resource)
    default_type: int  # Default type to use when creating new values


# Mapping of USS properties to their expected types
# Based on Unity's USS reference: https://docs.unity3d.com/Manual/UIE-USS-Properties-Reference.html
PROPERTY_TYPE_MAP: Dict[str, PropertyType] = {
    # Font properties
    "font-size": PropertyType("font-size", [2], 2),  # Float with unit
    "-unity-font": PropertyType("-unity-font", [7], 7),  # Resource reference
    "-unity-font-definition": PropertyType(
        "-unity-font-definition", [7], 7
    ),  # Resource reference
    "-unity-font-style": PropertyType("-unity-font-style", [1, 8], 1),  # Keyword/enum
    "font-weight": PropertyType(
        "font-weight", [2, 1, 8], 2
    ),  # Float or keyword (normal, bold)
    # Text properties
    "color": PropertyType("color", [4], 4),  # Color
    "-unity-text-align": PropertyType("-unity-text-align", [1, 8], 1),  # Keyword
    "-unity-text-outline-width": PropertyType(
        "-unity-text-outline-width", [2], 2
    ),  # Float
    "-unity-text-outline-color": PropertyType(
        "-unity-text-outline-color", [4], 4
    ),  # Color
    "white-space": PropertyType("white-space", [1, 8], 1),  # Keyword
    # Dimension properties
    "width": PropertyType("width", [2, 1, 8], 2),  # Float or keyword (auto)
    "height": PropertyType("height", [2, 1, 8], 2),  # Float or keyword (auto)
    "min-width": PropertyType("min-width", [2, 1, 8], 2),
    "min-height": PropertyType("min-height", [2, 1, 8], 2),
    "max-width": PropertyType("max-width", [2, 1, 8], 2),
    "max-height": PropertyType("max-height", [2, 1, 8], 2),
    # Padding properties
    "padding": PropertyType("padding", [2], 2),  # Shorthand
    "padding-top": PropertyType("padding-top", [2], 2),
    "padding-right": PropertyType("padding-right", [2], 2),
    "padding-bottom": PropertyType("padding-bottom", [2], 2),
    "padding-left": PropertyType("padding-left", [2], 2),
    # Margin properties
    "margin": PropertyType("margin", [2, 1, 8], 2),  # Shorthand, can be keyword (auto)
    "margin-top": PropertyType("margin-top", [2, 1, 8], 2),
    "margin-right": PropertyType("margin-right", [2, 1, 8], 2),
    "margin-bottom": PropertyType("margin-bottom", [2, 1, 8], 2),
    "margin-left": PropertyType("margin-left", [2, 1, 8], 2),
    # Border properties
    "border-width": PropertyType("border-width", [2], 2),  # Shorthand
    "border-top-width": PropertyType("border-top-width", [2], 2),
    "border-right-width": PropertyType("border-right-width", [2], 2),
    "border-bottom-width": PropertyType("border-bottom-width", [2], 2),
    "border-left-width": PropertyType("border-left-width", [2], 2),
    "border-radius": PropertyType("border-radius", [2], 2),  # Shorthand
    "border-top-left-radius": PropertyType("border-top-left-radius", [2], 2),
    "border-top-right-radius": PropertyType("border-top-right-radius", [2], 2),
    "border-bottom-left-radius": PropertyType("border-bottom-left-radius", [2], 2),
    "border-bottom-right-radius": PropertyType("border-bottom-right-radius", [2], 2),
    "border-color": PropertyType("border-color", [4], 4),  # Shorthand, color
    "border-top-color": PropertyType("border-top-color", [4], 4),
    "border-right-color": PropertyType("border-right-color", [4], 4),
    "border-bottom-color": PropertyType("border-bottom-color", [4], 4),
    "border-left-color": PropertyType("border-left-color", [4], 4),
    # Background properties
    "background-color": PropertyType("background-color", [4], 4),  # Color
    "background-image": PropertyType("background-image", [7], 7),  # Resource
    "-unity-background-image-tint-color": PropertyType(
        "-unity-background-image-tint-color", [4], 4
    ),
    "-unity-background-scale-mode": PropertyType(
        "-unity-background-scale-mode", [1, 8], 1
    ),  # Keyword
    # Visual effects
    "opacity": PropertyType("opacity", [2], 2),  # Float (0-1)
    "visibility": PropertyType("visibility", [1, 8], 1),  # Keyword (visible, hidden)
    "display": PropertyType("display", [1, 8], 1),  # Keyword (flex, none)
    "overflow": PropertyType(
        "overflow", [1, 8], 1
    ),  # Keyword (visible, hidden, scroll)
    # Position and layout
    "position": PropertyType("position", [1, 8], 1),  # Keyword (relative, absolute)
    "left": PropertyType("left", [2, 1, 8], 2),  # Float or keyword (auto)
    "top": PropertyType("top", [2, 1, 8], 2),
    "right": PropertyType("right", [2, 1, 8], 2),
    "bottom": PropertyType("bottom", [2, 1, 8], 2),
    "flex-direction": PropertyType("flex-direction", [1, 8], 1),  # Keyword
    "flex-wrap": PropertyType("flex-wrap", [1, 8], 1),  # Keyword
    "flex-grow": PropertyType("flex-grow", [2], 2),  # Float
    "flex-shrink": PropertyType("flex-shrink", [2], 2),  # Float
    "flex-basis": PropertyType("flex-basis", [2, 1, 8], 2),  # Float or keyword (auto)
    "align-items": PropertyType("align-items", [1, 8], 1),  # Keyword
    "align-self": PropertyType("align-self", [1, 8], 1),  # Keyword
    "justify-content": PropertyType("justify-content", [1, 8], 1),  # Keyword
    # Transform properties
    "rotate": PropertyType("rotate", [2], 2),  # Angle (float in degrees)
    "scale": PropertyType("scale", [2], 2),  # Scale factor (float)
    "translate": PropertyType("translate", [2], 2),  # X and Y translation
    "transform-origin": PropertyType("transform-origin", [2], 2),  # X and Y origin
    # Transition properties
    "transition-property": PropertyType(
        "transition-property", [8], 8
    ),  # Property name(s)
    "transition-duration": PropertyType(
        "transition-duration", [2], 2
    ),  # Time in seconds
    "transition-timing-function": PropertyType(
        "transition-timing-function", [1, 8], 1
    ),  # Keyword/function
    "transition-delay": PropertyType("transition-delay", [2], 2),  # Time in seconds
    # Cursor
    "cursor": PropertyType("cursor", [1, 8, 7], 1),  # Keyword or resource
    # Text overflow
    "text-overflow": PropertyType(
        "text-overflow", [1, 8], 1
    ),  # Keyword (clip, ellipsis)
    # Unity-specific slice properties for 9-slice scaling
    "-unity-slice-left": PropertyType("-unity-slice-left", [2], 2),
    "-unity-slice-top": PropertyType("-unity-slice-top", [2], 2),
    "-unity-slice-right": PropertyType("-unity-slice-right", [2], 2),
    "-unity-slice-bottom": PropertyType("-unity-slice-bottom", [2], 2),
    # Unity-specific paragraph properties
    "-unity-paragraph-spacing": PropertyType("-unity-paragraph-spacing", [2], 2),
    "-unity-text-overflow-position": PropertyType(
        "-unity-text-overflow-position", [1, 8], 1
    ),
}


class PropertyHandler:
    """Base class for handling property value application."""

    def can_handle(self, property_name: str) -> bool:
        """Check if this handler can handle the given property."""
        raise NotImplementedError

    def apply(
        self,
        data: Any,
        property_name: str,
        value: Any,
        value_index: Optional[int] = None,
    ) -> bool:
        """
        Apply a property value to a Unity stylesheet data object.

        Returns True if a change was made, False otherwise.
        """
        raise NotImplementedError


class FloatPropertyHandler(PropertyHandler):
    """Handler for float/numeric properties."""

    def can_handle(self, property_name: str) -> bool:
        prop_type = PROPERTY_TYPE_MAP.get(property_name)
        return prop_type is not None and 2 in prop_type.unity_types

    def apply(
        self,
        data: Any,
        property_name: str,
        value: Any,
        value_index: Optional[int] = None,
    ) -> bool:
        """Apply a float value to the stylesheet."""
        # Parse the value if it's a string
        if isinstance(value, str):
            parsed = parse_float_value(value)
            if parsed is None:
                log.warning(
                    f"Could not parse float value '{value}' for property '{property_name}'"
                )
                return False
            float_value = parsed.unity_value
        elif isinstance(value, FloatValue):
            float_value = value.unity_value
        elif isinstance(value, (int, float)):
            float_value = float(value)
        else:
            log.warning(
                f"Unsupported value type {type(value)} for float property '{property_name}'"
            )
            return False

        # Get or create floats array
        floats = getattr(data, "floats", [])
        if not hasattr(data, "floats"):
            setattr(data, "floats", floats)

        if value_index is not None and 0 <= value_index < len(floats):
            # Update existing float
            old_value = floats[value_index]
            if abs(old_value - float_value) < 1e-6:  # No change
                return False
            floats[value_index] = float_value
            log.info(
                f"  [PATCHED - float] {property_name} (index {value_index}): {old_value} → {float_value}"
            )
            return True
        else:
            # Append new float
            floats.append(float_value)
            new_index = len(floats) - 1
            log.info(
                f"  [PATCHED - float] {property_name} (new index {new_index}): → {float_value}"
            )
            return True


class KeywordPropertyHandler(PropertyHandler):
    """Handler for keyword/enum properties."""

    def can_handle(self, property_name: str) -> bool:
        prop_type = PROPERTY_TYPE_MAP.get(property_name)
        return prop_type is not None and (
            1 in prop_type.unity_types or 8 in prop_type.unity_types
        )

    def apply(
        self,
        data: Any,
        property_name: str,
        value: Any,
        value_index: Optional[int] = None,
    ) -> bool:
        """Apply a keyword/enum value to the stylesheet."""
        # Parse the value if it's a string
        if isinstance(value, str):
            parsed = parse_keyword_value(value)
            if parsed is None:
                log.warning(
                    f"Could not parse keyword value '{value}' for property '{property_name}'"
                )
                return False
            keyword = parsed.keyword
        elif isinstance(value, KeywordValue):
            keyword = value.keyword
        else:
            log.warning(
                f"Unsupported value type {type(value)} for keyword property '{property_name}'"
            )
            return False

        # Keywords are stored in the strings array
        strings = getattr(data, "strings", [])
        if not hasattr(data, "strings"):
            setattr(data, "strings", strings)

        if value_index is not None and 0 <= value_index < len(strings):
            # Update existing keyword
            old_value = strings[value_index]
            if old_value == keyword:  # No change
                return False
            strings[value_index] = keyword
            log.info(
                f"  [PATCHED - keyword] {property_name} (index {value_index}): {old_value} → {keyword}"
            )
            return True
        else:
            # Append new keyword
            strings.append(keyword)
            new_index = len(strings) - 1
            log.info(
                f"  [PATCHED - keyword] {property_name} (new index {new_index}): → {keyword}"
            )
            return True


class ResourcePropertyHandler(PropertyHandler):
    """Handler for resource reference properties (fonts, images)."""

    def can_handle(self, property_name: str) -> bool:
        prop_type = PROPERTY_TYPE_MAP.get(property_name)
        return prop_type is not None and 7 in prop_type.unity_types

    def apply(
        self,
        data: Any,
        property_name: str,
        value: Any,
        value_index: Optional[int] = None,
    ) -> bool:
        """Apply a resource reference to the stylesheet."""
        # Parse the value if it's a string
        if isinstance(value, str):
            parsed = parse_resource_value(value)
            if parsed is None:
                log.warning(
                    f"Could not parse resource value '{value}' for property '{property_name}'"
                )
                return False
            resource_path = parsed.unity_path
        elif isinstance(value, ResourceValue):
            resource_path = value.unity_path
        else:
            log.warning(
                f"Unsupported value type {type(value)} for resource property '{property_name}'"
            )
            return False

        # Resources are stored in the strings array
        strings = getattr(data, "strings", [])
        if not hasattr(data, "strings"):
            setattr(data, "strings", strings)

        if value_index is not None and 0 <= value_index < len(strings):
            # Update existing resource
            old_value = strings[value_index]
            if old_value == resource_path:  # No change
                return False
            strings[value_index] = resource_path
            log.info(
                f"  [PATCHED - resource] {property_name} (index {value_index}): {old_value} → {resource_path}"
            )
            return True
        else:
            # Append new resource
            strings.append(resource_path)
            new_index = len(strings) - 1
            log.info(
                f"  [PATCHED - resource] {property_name} (new index {new_index}): → {resource_path}"
            )
            return True


# Registry of property handlers
_HANDLERS: List[PropertyHandler] = [
    FloatPropertyHandler(),
    KeywordPropertyHandler(),
    ResourcePropertyHandler(),
]


def get_property_handler(property_name: str) -> Optional[PropertyHandler]:
    """Get the appropriate handler for a given property name."""
    for handler in _HANDLERS:
        if handler.can_handle(property_name):
            return handler
    return None


def apply_property_value(
    data: Any,
    property_name: str,
    value: Any,
    value_index: Optional[int] = None,
) -> bool:
    """
    Apply a property value to a Unity stylesheet, automatically detecting the type.

    Args:
        data: The Unity stylesheet data object
        property_name: The CSS property name
        value: The value to apply (can be string, ParsedValue, or typed value)
        value_index: Optional index in the appropriate array (floats/strings/colors)

    Returns:
        True if a change was made, False otherwise
    """
    # First check if it's a color (backwards compatibility)
    if isinstance(value, str):
        normalized_color = normalize_css_color(value)
        if normalized_color:
            # Handle as color (existing logic)
            # This is handled by the existing CSS patcher
            return False

    # Get the appropriate handler
    handler = get_property_handler(property_name)
    if handler is None:
        log.debug(f"No handler found for property '{property_name}'")
        return False

    return handler.apply(data, property_name, value, value_index)
