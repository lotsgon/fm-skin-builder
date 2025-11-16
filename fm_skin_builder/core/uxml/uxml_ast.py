"""
UXML Abstract Syntax Tree (AST) Data Structures

These classes represent the parsed structure of UXML documents in a way
that can be round-tripped between Unity's VisualTreeAsset format and
editable XML text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class UXMLElementType(str, Enum):
    """Known Unity UI Toolkit element types."""

    VISUAL_ELEMENT = "VisualElement"
    LABEL = "Label"
    BUTTON = "Button"
    TOGGLE = "Toggle"
    TEXT_FIELD = "TextField"
    SCROLL_VIEW = "ScrollView"
    LIST_VIEW = "ListView"
    TREE_VIEW = "TreeView"
    DROPDOWN_FIELD = "DropdownField"
    SLIDER = "Slider"
    SLIDER_INT = "SliderInt"
    MIN_MAX_SLIDER = "MinMaxSlider"
    PROGRESS_BAR = "ProgressBar"
    FOLDOUT = "Foldout"
    BOX = "Box"
    IMAGE = "Image"
    TEMPLATE = "Template"
    INSTANCE = "Instance"
    IMGUI_CONTAINER = "IMGUIContainer"

    # Custom SI types (if encountered)
    CUSTOM = "Custom"


@dataclass
class UXMLAttribute:
    """
    Represents a single UXML attribute (Unity calls these "UxmlTraits").

    Examples:
        name="my-element"
        class="button primary"
        style="background-color: red;"
    """

    name: str
    value: str

    # Unity internal data (for round-tripping)
    trait_type: Optional[int] = None  # Unity's trait type ID

    def __str__(self) -> str:
        """Render as XML attribute."""
        # Escape XML special characters
        escaped_value = (
            self.value
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f'{self.name}="{escaped_value}"'


@dataclass
class UXMLElement:
    """
    Represents a UXML element in the hierarchy.

    Corresponds to Unity's VisualElementAsset or derived types.
    """

    # Element type (VisualElement, Label, Button, etc.)
    element_type: str

    # Attributes (name, class, style, etc.)
    attributes: List[UXMLAttribute] = field(default_factory=list)

    # Child elements
    children: List[UXMLElement] = field(default_factory=list)

    # Text content (for Label, Button, etc.)
    text: Optional[str] = None

    # Unity internal data (for round-tripping)
    order_in_document: Optional[int] = None
    parent_id: Optional[int] = None
    id: Optional[int] = None

    # Template reference (if this is a Template instance)
    template_asset: Optional[str] = None
    template_guid: Optional[str] = None

    def get_attribute(self, name: str) -> Optional[str]:
        """Get attribute value by name."""
        for attr in self.attributes:
            if attr.name == name:
                return attr.value
        return None

    def set_attribute(self, name: str, value: str) -> None:
        """Set attribute value, creating it if it doesn't exist."""
        for attr in self.attributes:
            if attr.name == name:
                attr.value = value
                return
        self.attributes.append(UXMLAttribute(name=name, value=value))

    def get_classes(self) -> List[str]:
        """Get list of CSS classes applied to this element."""
        class_attr = self.get_attribute("class")
        if class_attr:
            return [c.strip() for c in class_attr.split() if c.strip()]
        return []

    def add_class(self, class_name: str) -> None:
        """Add a CSS class to this element."""
        classes = self.get_classes()
        if class_name not in classes:
            classes.append(class_name)
            self.set_attribute("class", " ".join(classes))

    def remove_class(self, class_name: str) -> None:
        """Remove a CSS class from this element."""
        classes = self.get_classes()
        if class_name in classes:
            classes.remove(class_name)
            if classes:
                self.set_attribute("class", " ".join(classes))
            else:
                # Remove the class attribute entirely
                self.attributes = [a for a in self.attributes if a.name != "class"]


@dataclass
class UXMLTemplate:
    """
    Represents a UXML template reference.

    Templates are reusable UI fragments defined in other UXML files.
    """

    name: str
    src: str  # Path to template UXML file
    guid: Optional[str] = None
    file_id: Optional[int] = None


@dataclass
class UXMLDocument:
    """
    Represents a complete UXML document.

    This corresponds to Unity's VisualTreeAsset at the top level.
    """

    # Root element(s)
    root: Optional[UXMLElement] = None

    # Template references used in this document
    templates: List[UXMLTemplate] = field(default_factory=list)

    # Stylesheet references (USS files)
    stylesheets: List[str] = field(default_factory=list)  # List of GUIDs or paths

    # Inline styles (compiled into a StyleSheet)
    inline_styles: Optional[str] = None

    # Unity metadata (for round-tripping)
    asset_name: Optional[str] = None
    guid: Optional[str] = None
    file_id: Optional[int] = None
    path_id: Optional[int] = None
    bundle: Optional[str] = None

    # Content hash (for change detection)
    content_hash: Optional[str] = None

    def get_all_elements(self) -> List[UXMLElement]:
        """Get all elements in the document via DFS."""
        if not self.root:
            return []

        elements = []
        stack = [self.root]

        while stack:
            elem = stack.pop()
            elements.append(elem)
            # Add children in reverse order to maintain DFS order
            stack.extend(reversed(elem.children))

        return elements

    def find_elements_by_type(self, element_type: str) -> List[UXMLElement]:
        """Find all elements of a specific type."""
        return [
            elem for elem in self.get_all_elements()
            if elem.element_type == element_type
        ]

    def find_elements_by_class(self, class_name: str) -> List[UXMLElement]:
        """Find all elements with a specific CSS class."""
        return [
            elem for elem in self.get_all_elements()
            if class_name in elem.get_classes()
        ]

    def find_element_by_name(self, name: str) -> Optional[UXMLElement]:
        """Find first element with a specific name attribute."""
        for elem in self.get_all_elements():
            if elem.get_attribute("name") == name:
                return elem
        return None


@dataclass
class StyleRule:
    """
    Represents a CSS style rule (selector + properties).

    This is used for inline styles extracted from Unity StyleSheets.
    """

    selector: str  # CSS selector (e.g., ".button", "#my-id", "Label")
    properties: Dict[str, str] = field(default_factory=dict)

    # Unity internal data
    rule_index: Optional[int] = None

    def to_css(self, indent: int = 0) -> str:
        """Render as CSS text."""
        indent_str = "  " * indent
        lines = [f"{indent_str}{self.selector} {{"]

        for prop, value in sorted(self.properties.items()):
            lines.append(f"{indent_str}  {prop}: {value};")

        lines.append(f"{indent_str}}}")
        return "\n".join(lines)


@dataclass
class InlineStyle:
    """
    Represents inline style properties on a single element.

    This is the style="..." attribute content.
    """

    properties: Dict[str, str] = field(default_factory=dict)

    def to_css(self) -> str:
        """Render as inline style string."""
        return "; ".join(f"{k}: {v}" for k, v in sorted(self.properties.items()))

    @classmethod
    def from_css(cls, css_text: str) -> InlineStyle:
        """Parse inline style from CSS text."""
        properties = {}

        # Split by semicolon and parse each property
        for decl in css_text.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue

            prop, value = decl.split(":", 1)
            properties[prop.strip()] = value.strip()

        return cls(properties=properties)
