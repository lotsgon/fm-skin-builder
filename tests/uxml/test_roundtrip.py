"""
Round-trip tests for UXML export → edit → import pipeline.

Tests that UXML can be exported, modified, and reimported without data loss.
"""

import pytest
from pathlib import Path
from fm_skin_builder.core.uxml import (
    UXMLExporter,
    UXMLImporter,
    UXMLDocument,
    UXMLElement,
    UXMLAttribute,
)
from fm_skin_builder.core.uxml.style_serializer import StyleSerializer


class TestUXMLRoundTrip:
    """Test UXML round-trip conversion."""

    def test_simple_element_roundtrip(self):
        """Test round-trip of a simple element."""
        # Create a simple UXML document
        root = UXMLElement(
            element_type="VisualElement",
            attributes=[
                UXMLAttribute(name="name", value="root"),
                UXMLAttribute(name="class", value="container"),
            ]
        )

        doc = UXMLDocument(
            asset_name="TestDoc",
            root=root
        )

        # Export to XML
        exporter = UXMLExporter()
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.uxml', delete=False) as f:
            uxml_path = Path(f.name)

        try:
            exporter.write_uxml(doc, uxml_path)

            # Import back
            importer = UXMLImporter()
            imported_doc = importer.import_uxml(uxml_path)

            # Verify
            # Note: asset_name comes from filename when importing, which is fine
            assert imported_doc.root is not None
            assert imported_doc.root.element_type == "VisualElement"
            assert imported_doc.root.get_attribute("name") == "root"
            assert "container" in imported_doc.root.get_classes()

        finally:
            uxml_path.unlink(missing_ok=True)

    def test_nested_elements_roundtrip(self):
        """Test round-trip of nested elements."""
        # Create nested structure
        child1 = UXMLElement(
            element_type="Label",
            attributes=[UXMLAttribute(name="text", value="Hello")],
            text="Hello"
        )

        child2 = UXMLElement(
            element_type="Button",
            attributes=[UXMLAttribute(name="text", value="Click me")],
            text="Click me"
        )

        root = UXMLElement(
            element_type="VisualElement",
            children=[child1, child2]
        )

        doc = UXMLDocument(root=root)

        # Export and import
        exporter = UXMLExporter()
        importer = UXMLImporter()

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.uxml', delete=False) as f:
            uxml_path = Path(f.name)

        try:
            exporter.write_uxml(doc, uxml_path)
            imported_doc = importer.import_uxml(uxml_path)

            # Verify structure
            assert len(imported_doc.root.children) == 2
            assert imported_doc.root.children[0].element_type == "Label"
            assert imported_doc.root.children[1].element_type == "Button"

        finally:
            uxml_path.unlink(missing_ok=True)

    def test_uxml_text_roundtrip(self):
        """Test round-trip using text strings."""
        uxml_text = """<?xml version="1.0"?>
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="root" class="container">
    <ui:Label text="Hello World" />
    <ui:Button text="Click me" class="primary-button" />
  </ui:VisualElement>
</ui:UXML>"""

        # Import
        importer = UXMLImporter()
        doc = importer.import_uxml_text(uxml_text, "TestDoc")

        # Verify
        assert doc.root is not None
        assert doc.root.element_type == "VisualElement"
        assert doc.root.get_attribute("name") == "root"
        assert len(doc.root.children) == 2

        # Export back
        exporter = UXMLExporter()
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.uxml', delete=False) as f:
            uxml_path = Path(f.name)

        try:
            exporter.write_uxml(doc, uxml_path)
            exported_text = uxml_path.read_text()

            # Verify exported text contains key elements
            assert "VisualElement" in exported_text
            assert "Label" in exported_text
            assert "Button" in exported_text
            assert 'name="root"' in exported_text

        finally:
            uxml_path.unlink(missing_ok=True)

    def test_class_manipulation(self):
        """Test adding/removing CSS classes."""
        root = UXMLElement(
            element_type="VisualElement",
            attributes=[UXMLAttribute(name="class", value="foo bar")]
        )

        # Verify initial classes
        assert root.get_classes() == ["foo", "bar"]

        # Add class
        root.add_class("baz")
        assert "baz" in root.get_classes()

        # Remove class
        root.remove_class("foo")
        assert "foo" not in root.get_classes()
        assert "bar" in root.get_classes()

    def test_element_finding(self):
        """Test finding elements in document."""
        # Create structure
        button1 = UXMLElement(
            element_type="Button",
            attributes=[
                UXMLAttribute(name="name", value="submit-button"),
                UXMLAttribute(name="class", value="primary"),
            ]
        )

        button2 = UXMLElement(
            element_type="Button",
            attributes=[UXMLAttribute(name="class", value="secondary")]
        )

        label = UXMLElement(
            element_type="Label",
            attributes=[UXMLAttribute(name="class", value="primary")]
        )

        root = UXMLElement(
            element_type="VisualElement",
            children=[button1, button2, label]
        )

        doc = UXMLDocument(root=root)

        # Test finding by type
        buttons = doc.find_elements_by_type("Button")
        assert len(buttons) == 2

        # Test finding by class
        primary_elements = doc.find_elements_by_class("primary")
        assert len(primary_elements) == 2

        # Test finding by name
        submit = doc.find_element_by_name("submit-button")
        assert submit is not None
        assert submit.element_type == "Button"


class TestStyleParsing:
    """Test CSS/StyleSheet parsing."""

    def test_parse_simple_css(self):
        """Test parsing simple CSS."""
        serializer = StyleSerializer()

        css_text = """
.button {
    background-color: #1976d2;
    color: #ffffff;
}

#my-id {
    width: 100px;
    height: 50px;
}
"""

        rules = serializer.parse_css(css_text)

        assert len(rules) == 2
        assert rules[0]['selector'] == '.button'
        assert 'background-color' in rules[0]['properties']
        assert rules[1]['selector'] == '#my-id'

    def test_css_variable_parsing(self):
        """Test CSS variable parsing."""
        serializer = StyleSerializer()

        css_text = """
:root {
    --primary-color: #1976d2;
    --secondary-color: #dc004e;
}

.button {
    background-color: var(--primary-color);
}
"""

        rules = serializer.parse_css(css_text)

        # Find button rule
        button_rule = next(r for r in rules if r['selector'] == '.button')
        assert 'background-color' in button_rule['properties']

    def test_hex_color_parsing(self):
        """Test hex color parsing."""
        serializer = StyleSerializer()

        # RGB
        color_rgb = serializer._parse_hex_color("#1976d2")
        assert color_rgb is not None
        assert len(color_rgb) == 4
        assert color_rgb[3] == 1.0  # Alpha should be 1.0

        # RGBA
        color_rgba = serializer._parse_hex_color("#1976d2ff")
        assert color_rgba is not None
        assert len(color_rgba) == 4

    def test_selector_parsing(self):
        """Test CSS selector parsing."""
        serializer = StyleSerializer()

        # Class selector
        parts = serializer._parse_selector(".button")
        assert any(p['m_Type'] == 2 and p['m_Value'] == 'button' for p in parts)

        # ID selector
        parts = serializer._parse_selector("#my-id")
        assert any(p['m_Type'] == 3 and p['m_Value'] == 'my-id' for p in parts)

        # Type selector
        parts = serializer._parse_selector("Label")
        assert any(p['m_Type'] == 1 and p['m_Value'] == 'Label' for p in parts)

        # Descendant selector
        parts = serializer._parse_selector("VisualElement Label")
        # Should have type parts and a descendant combinator
        type_parts = [p for p in parts if p['m_Type'] == 1]
        assert len(type_parts) >= 1


class TestInlineStyles:
    """Test inline style handling."""

    def test_inline_style_parsing(self):
        """Test parsing inline styles."""
        from fm_skin_builder.core.uxml.uxml_ast import InlineStyle

        css = "background-color: red; width: 100px; height: 50px"
        style = InlineStyle.from_css(css)

        assert style.properties['background-color'] == 'red'
        assert style.properties['width'] == '100px'
        assert style.properties['height'] == '50px'

    def test_inline_style_rendering(self):
        """Test rendering inline styles."""
        from fm_skin_builder.core.uxml.uxml_ast import InlineStyle

        style = InlineStyle(properties={
            'background-color': 'red',
            'width': '100px'
        })

        css = style.to_css()
        assert 'background-color: red' in css
        assert 'width: 100px' in css


class TestValueSerialization:
    """Test value type serialization."""

    def test_float_value_serialization(self):
        """Test float value serialization."""
        serializer = StyleSerializer()
        strings = []
        colors = []
        string_map = {}
        color_map = {}

        value_type, value_index, value_data = serializer._serialize_value(
            "0.5",
            strings,
            colors,
            string_map,
            color_map
        )

        assert value_type == StyleSerializer.VALUE_TYPE_FLOAT
        assert value_data == 0.5

    def test_dimension_value_serialization(self):
        """Test dimension value serialization."""
        serializer = StyleSerializer()
        strings = []
        colors = []
        string_map = {}
        color_map = {}

        value_type, value_index, value_data = serializer._serialize_value(
            "100px",
            strings,
            colors,
            string_map,
            color_map
        )

        assert value_type == StyleSerializer.VALUE_TYPE_DIMENSION
        assert strings[value_index] == "100px"

    def test_color_value_serialization(self):
        """Test color value serialization."""
        serializer = StyleSerializer()
        strings = []
        colors = []
        string_map = {}
        color_map = {}

        value_type, value_index, value_data = serializer._serialize_value(
            "#1976d2",
            strings,
            colors,
            string_map,
            color_map
        )

        assert value_type == StyleSerializer.VALUE_TYPE_COLOR
        assert len(colors) == 1

    def test_variable_value_serialization(self):
        """Test CSS variable serialization."""
        serializer = StyleSerializer()
        strings = []
        colors = []
        string_map = {}
        color_map = {}

        value_type, value_index, value_data = serializer._serialize_value(
            "var(--primary-color)",
            strings,
            colors,
            string_map,
            color_map
        )

        assert value_type == StyleSerializer.VALUE_TYPE_VARIABLE
        assert strings[value_index].startswith("--")

    def test_resource_value_serialization(self):
        """Test resource URL serialization."""
        serializer = StyleSerializer()
        strings = []
        colors = []
        string_map = {}
        color_map = {}

        value_type, value_index, value_data = serializer._serialize_value(
            "url(background.png)",
            strings,
            colors,
            string_map,
            color_map
        )

        assert value_type == StyleSerializer.VALUE_TYPE_RESOURCE
        assert strings[value_index] == "background.png"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
