"""
Value parsers for different Unity StyleSheet (USS) property types.

Unity StyleSheet supports multiple value types:
- Type 1: Keyword/Enum (e.g., "visible", "hidden", "bold")
- Type 2: Float with optional unit (e.g., "12px", "1.5em", "100%", "0.5")
- Type 3: String variable reference (e.g., "var(--my-color)")
- Type 4: Color (e.g., "#FF0000", "rgba(255, 0, 0, 1)")
- Type 7: Resource reference (e.g., "url('resource://fonts/MyFont')")
- Type 8: Enum (similar to Type 1)
- Type 10: Variable reference (similar to Type 3)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, List, Tuple

from .logger import get_logger

log = get_logger(__name__)

__all__ = [
    "CssValueType",
    "ParsedValue",
    "FloatValue",
    "KeywordValue",
    "ResourceValue",
    "VariableValue",
    "parse_css_value",
    "parse_float_value",
    "parse_keyword_value",
    "parse_resource_value",
    "parse_variable_value",
]


class CssValueType(Enum):
    """Unity StyleSheet value types."""

    KEYWORD = 1  # Enum/boolean keywords
    FLOAT = 2  # Numeric values with optional units
    STRING = 3  # String variable references
    COLOR = 4  # Color values (handled by existing code)
    RESOURCE = 7  # Resource references (fonts, images, etc.)
    ENUM = 8  # Enum values
    VARIABLE = 10  # Variable references


@dataclass
class FloatValue:
    """Represents a float value with optional unit."""

    value: float
    unit: Optional[str] = None  # px, em, %, etc.

    def __str__(self) -> str:
        if self.unit:
            return f"{self.value}{self.unit}"
        return str(self.value)

    @property
    def unity_value(self) -> float:
        """Get the value in Unity's expected format (typically pixels or unitless)."""
        # Unity USS typically expects pixel values or unitless floats
        # For now, return the raw value - conversion logic can be added later
        return self.value


@dataclass
class KeywordValue:
    """Represents a keyword/enum value."""

    keyword: str

    def __str__(self) -> str:
        return self.keyword


@dataclass
class ResourceValue:
    """Represents a resource reference (url(...))."""

    path: str
    resource_type: Optional[str] = None  # 'font', 'image', etc.

    def __str__(self) -> str:
        return f"url('{self.path}')"

    @property
    def unity_path(self) -> str:
        """Get the path in Unity's expected format."""
        # Unity expects paths like "resource://fonts/FontName"
        if self.path.startswith("resource://"):
            return self.path
        # If it's a relative path, convert to resource:// format
        return f"resource://{self.path}"


@dataclass
class VariableValue:
    """Represents a CSS variable reference (var(--name))."""

    variable_name: str

    def __str__(self) -> str:
        return f"var({self.variable_name})"

    @property
    def unity_variable_name(self) -> str:
        """Get the variable name in Unity's expected format (with -- prefix)."""
        # Ensure variable name has -- prefix
        if not self.variable_name.startswith("--"):
            return f"--{self.variable_name}"
        return self.variable_name


@dataclass
class ParsedValue:
    """Container for a parsed CSS value with type information."""

    value: Union[FloatValue, KeywordValue, ResourceValue, VariableValue, str]
    value_type: CssValueType
    raw: str

    def __str__(self) -> str:
        return str(self.value)


# Regex patterns for parsing
_FLOAT_PATTERN = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))([a-zA-Z%]*)$")
_URL_PATTERN = re.compile(r'^url\s*\(\s*["\']?([^"\'()]+)["\']?\s*\)$', re.IGNORECASE)
_RESOURCE_PATTERN = re.compile(r"^resource://([^/]+)/(.+)$", re.IGNORECASE)
_VAR_PATTERN = re.compile(r"^var\s*\(\s*(--[\w-]+)\s*\)$", re.IGNORECASE)

# Known CSS/USS units
VALID_UNITS = {
    "px",  # Pixels
    "em",  # Relative to font size
    "rem",  # Relative to root font size
    "%",  # Percentage
    "pt",  # Points
    "vw",  # Viewport width
    "vh",  # Viewport height
}

# Known USS keywords for various properties
VALID_KEYWORDS = {
    # Display/visibility
    "none",
    "flex",
    "inline",
    "block",
    "inline-block",
    "visible",
    "hidden",
    # Text alignment
    "left",
    "right",
    "center",
    "justify",
    "upper-left",
    "upper-center",
    "upper-right",
    "middle-left",
    "middle-center",
    "middle-right",
    "lower-left",
    "lower-center",
    "lower-right",
    # Font style
    "normal",
    "italic",
    "bold",
    "bold-and-italic",
    # Overflow
    "scroll",
    "clip",
    "ellipsis",
    # Position
    "relative",
    "absolute",
    "static",
    # White space
    "nowrap",
    "pre",
    "pre-wrap",
    "pre-line",
    # Scale mode
    "stretch-to-fill",
    "scale-and-crop",
    "scale-to-fit",
    # Boolean-like
    "true",
    "false",
    "auto",
    "initial",
    "inherit",
}


def parse_float_value(value_str: str) -> Optional[FloatValue]:
    """
    Parse a float value with optional unit.

    Examples:
        - "12px" -> FloatValue(12.0, "px")
        - "1.5em" -> FloatValue(1.5, "em")
        - "100%" -> FloatValue(100.0, "%")
        - "0.5" -> FloatValue(0.5, None)
        - "42" -> FloatValue(42.0, None)

    Args:
        value_str: The CSS value string to parse

    Returns:
        FloatValue if parsing succeeds, None otherwise
    """
    value_str = value_str.strip()
    if not value_str:
        return None

    match = _FLOAT_PATTERN.match(value_str)
    if not match:
        return None

    number_str, unit = match.groups()

    try:
        number = float(number_str)
    except ValueError:
        return None

    # Normalize unit
    unit = unit.lower() if unit else None

    # Validate unit if present
    if unit and unit not in VALID_UNITS:
        log.warning(
            f"Unknown unit '{unit}' in value '{value_str}', treating as unitless"
        )
        unit = None

    return FloatValue(value=number, unit=unit)


def parse_keyword_value(value_str: str) -> Optional[KeywordValue]:
    """
    Parse a keyword/enum value.

    Examples:
        - "visible" -> KeywordValue("visible")
        - "bold" -> KeywordValue("bold")
        - "center" -> KeywordValue("center")

    Args:
        value_str: The CSS value string to parse

    Returns:
        KeywordValue if the string is a known keyword, None otherwise
    """
    value_str = value_str.strip().lower()
    if not value_str:
        return None

    # Check if it's a known keyword
    if value_str in VALID_KEYWORDS:
        return KeywordValue(keyword=value_str)

    # Also accept Unity-specific enum values with dashes
    if re.match(r"^[a-z][a-z0-9-]*$", value_str):
        return KeywordValue(keyword=value_str)

    return None


def parse_resource_value(value_str: str) -> Optional[ResourceValue]:
    """
    Parse a resource reference (url(...)).

    Examples:
        - "url('resource://fonts/MyFont')" -> ResourceValue("resource://fonts/MyFont", "fonts")
        - "url(\"path/to/image.png\")" -> ResourceValue("path/to/image.png", None)
        - "url(my-font)" -> ResourceValue("my-font", None)

    Args:
        value_str: The CSS value string to parse

    Returns:
        ResourceValue if parsing succeeds, None otherwise
    """
    value_str = value_str.strip()
    if not value_str:
        return None

    match = _URL_PATTERN.match(value_str)
    if not match:
        return None

    path = match.group(1).strip()

    # Try to detect resource type from path
    resource_type = None
    resource_match = _RESOURCE_PATTERN.match(path)
    if resource_match:
        resource_type = resource_match.group(1)  # e.g., "fonts", "images"

    return ResourceValue(path=path, resource_type=resource_type)


def parse_variable_value(value_str: str) -> Optional[VariableValue]:
    """
    Parse a CSS variable reference (var(--name)).

    Examples:
        - "var(--my-color)" -> VariableValue("--my-color")
        - "var(--font-size)" -> VariableValue("--font-size")
        - "var( --spacing )" -> VariableValue("--spacing")

    Args:
        value_str: The CSS value string to parse

    Returns:
        VariableValue if parsing succeeds, None otherwise
    """
    value_str = value_str.strip()
    if not value_str:
        return None

    match = _VAR_PATTERN.match(value_str)
    if not match:
        return None

    variable_name = match.group(1).strip()
    return VariableValue(variable_name=variable_name)


def parse_css_value(
    value_str: str, property_name: Optional[str] = None
) -> Optional[ParsedValue]:
    """
    Parse a CSS value and determine its type.

    This function attempts to parse the value as different types in order:
    1. Variable reference (var(--name))
    2. Float (numeric with optional unit)
    3. Resource reference (url(...))
    4. Keyword/enum

    Args:
        value_str: The CSS value string to parse
        property_name: Optional property name for context (helps with type detection)

    Returns:
        ParsedValue containing the parsed value and type, or None if parsing fails
    """
    value_str = value_str.strip()
    if not value_str:
        return None

    # Try parsing as variable reference first (var(--name))
    var_val = parse_variable_value(value_str)
    if var_val is not None:
        return ParsedValue(
            value=var_val, value_type=CssValueType.VARIABLE, raw=value_str
        )

    # Try parsing as float (most common for dimensions)
    float_val = parse_float_value(value_str)
    if float_val is not None:
        return ParsedValue(
            value=float_val, value_type=CssValueType.FLOAT, raw=value_str
        )

    # Try parsing as resource reference
    resource_val = parse_resource_value(value_str)
    if resource_val is not None:
        return ParsedValue(
            value=resource_val, value_type=CssValueType.RESOURCE, raw=value_str
        )

    # Try parsing as keyword
    keyword_val = parse_keyword_value(value_str)
    if keyword_val is not None:
        return ParsedValue(
            value=keyword_val, value_type=CssValueType.KEYWORD, raw=value_str
        )

    # If nothing matches, return None
    log.debug(f"Could not parse CSS value '{value_str}' for property '{property_name}'")
    return None


def parse_multi_value(value_str: str) -> List[ParsedValue]:
    """
    Parse a multi-value CSS property (e.g., padding, margin).

    Examples:
        - "10px 20px" -> [FloatValue(10, "px"), FloatValue(20, "px")]
        - "1em 2em 3em 4em" -> [FloatValue(1, "em"), ...]

    Args:
        value_str: The CSS value string containing multiple values

    Returns:
        List of ParsedValue objects
    """
    value_str = value_str.strip()
    if not value_str:
        return []

    # Split on whitespace
    parts = value_str.split()

    parsed_values: List[ParsedValue] = []
    for part in parts:
        parsed = parse_css_value(part)
        if parsed:
            parsed_values.append(parsed)

    return parsed_values


def expand_shorthand_box(
    values: List[ParsedValue],
) -> Tuple[ParsedValue, ParsedValue, ParsedValue, ParsedValue]:
    """
    Expand CSS box model shorthand (padding, margin) to individual sides.

    CSS box model rules:
    - 1 value: all sides
    - 2 values: top/bottom, left/right
    - 3 values: top, left/right, bottom
    - 4 values: top, right, bottom, left (clockwise)

    Args:
        values: List of 1-4 ParsedValue objects

    Returns:
        Tuple of (top, right, bottom, left) ParsedValue objects
    """
    count = len(values)

    if count == 1:
        # All sides
        return values[0], values[0], values[0], values[0]
    elif count == 2:
        # top/bottom, left/right
        return values[0], values[1], values[0], values[1]
    elif count == 3:
        # top, left/right, bottom
        return values[0], values[1], values[2], values[1]
    elif count >= 4:
        # top, right, bottom, left
        return values[0], values[1], values[2], values[3]
    else:
        raise ValueError(f"Cannot expand shorthand with {count} values")
