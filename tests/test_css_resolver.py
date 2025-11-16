"""
Test CSS Resolver - Variable resolution and token extraction.
"""

import pytest
from fm_skin_builder.core.catalogue.css_resolver import (
    CSSResolver,
    resolve_css_class_properties,
)
from fm_skin_builder.core.catalogue.models import (
    CSSClass,
    CSSProperty,
    CSSValueDefinition,
)


class TestCSSResolver:
    """Test CSSResolver class."""

    def test_simple_variable_resolution(self):
        """Test resolving a simple variable reference."""
        resolver = CSSResolver({"--primary": "#1976D2"})

        resolved, variables = resolver.resolve_property_value("var(--primary)")

        assert resolved == "#1976D2"
        assert variables == {"--primary"}

    def test_nested_variable_resolution(self):
        """Test resolving nested variable references."""
        resolver = CSSResolver({
            "--primary": "#1976D2",
            "--accent": "var(--primary)",
        })

        resolved, variables = resolver.resolve_property_value("var(--accent)")

        assert resolved == "#1976D2"
        assert variables == {"--accent", "--primary"}

    def test_multiple_variable_resolution(self):
        """Test resolving multiple variables in one value."""
        resolver = CSSResolver({
            "--color1": "#FF0000",
            "--color2": "#00FF00",
        })

        value = "var(--color1) var(--color2)"
        resolved, variables = resolver.resolve_property_value(value)

        assert resolved == "#FF0000 #00FF00"
        assert variables == {"--color1", "--color2"}

    def test_variable_not_found(self):
        """Test handling of missing variables."""
        resolver = CSSResolver({"--primary": "#1976D2"})

        resolved, variables = resolver.resolve_property_value("var(--missing)")

        # Should keep the var() reference if not found
        assert "var(--missing)" in resolved
        assert variables == {"--missing"}

    def test_max_depth_protection(self):
        """Test that max depth prevents infinite loops."""
        # Create a circular reference
        resolver = CSSResolver({
            "--a": "var(--b)",
            "--b": "var(--a)",
        })

        # Should not hang
        resolved, variables = resolver.resolve_property_value("var(--a)", max_depth=5)

        assert resolved is not None
        assert "--a" in variables

    def test_extract_color_tokens(self):
        """Test extracting hex colors from values."""
        resolver = CSSResolver()

        colors = resolver.extract_color_tokens("#1976D2 #FFFFFF rgba(255, 0, 0, 0.5)")

        assert "#1976D2" in colors
        assert "#FFFFFF" in colors
        assert "rgba(255, 0, 0, 0.5)" in colors

    def test_extract_numeric_tokens(self):
        """Test extracting numeric tokens from values."""
        resolver = CSSResolver()

        tokens = resolver.extract_numeric_tokens("4px 10px 50% 2rem")

        assert "4px" in tokens
        assert "10px" in tokens
        assert "50%" in tokens
        assert "2rem" in tokens

    def test_extract_asset_references(self):
        """Test extracting asset references."""
        resolver = CSSResolver()

        # Test sprite:// URLs
        assets = resolver.extract_asset_references("sprite://FMImages_1x/star_full")
        assert "FMImages_1x/star_full" in assets

        # Test url() format
        assets = resolver.extract_asset_references("url('resource://Icons/home')")
        assert "Icons/home" in assets

    def test_build_property_summary(self):
        """Test building property summary."""
        resolver = CSSResolver({"--primary": "#1976D2"})

        raw_properties = {
            "color": "var(--primary)",
            "border-radius": "4px",
            "background-image": "sprite://FMImages_1x/star_full",
        }

        resolved_properties = {
            "color": "#1976D2",
            "border-radius": "4px",
            "background-image": "sprite://FMImages_1x/star_full",
        }

        summary = resolver.build_property_summary(raw_properties, resolved_properties)

        assert "#1976D2" in summary["colors"]
        assert "FMImages_1x/star_full" in summary["assets"]
        assert "--primary" in summary["variables"]
        assert "border-radius" in summary["layout"]

    def test_build_variable_registry(self):
        """Test building variable registry from CSSVariable objects."""
        from fm_skin_builder.core.catalogue.models import CSSVariable

        resolver = CSSResolver()

        var1 = CSSVariable(
            name="--primary",
            stylesheet="FMColours",
            bundle="test.bundle",
            property_name="--primary",
            rule_index=0,
            values=[CSSValueDefinition(value_type=4, index=0, resolved_value="#1976D2")],
            first_seen="2026.1.0",
            last_seen="2026.4.0",
        )

        registry = resolver.build_variable_registry([var1])

        assert registry["--primary"] == "#1976D2"

    def test_caching(self):
        """Test that resolution caching works."""
        resolver = CSSResolver({"--primary": "#1976D2"})

        # First resolution
        resolved1, _ = resolver.resolve_property_value("var(--primary)")

        # Second resolution should use cache
        resolved2, _ = resolver.resolve_property_value("var(--primary)")

        assert resolved1 == resolved2
        assert "var(--primary)" in resolver._resolution_cache


class TestResolveClassProperties:
    """Test resolve_css_class_properties function."""

    def test_resolve_css_class_properties(self):
        """Test resolving all properties of a CSS class."""
        # Create a mock CSS class
        css_class = CSSClass(
            name=".test-class",
            stylesheet="TestSheet",
            bundle="test.bundle",
            raw_properties={
                "color": "var(--primary)",
                "border-radius": "4px",
                "background-image": "sprite://test/icon",
            },
            first_seen="2026.1.0",
            last_seen="2026.4.0",
        )

        variable_registry = {"--primary": "#1976D2"}

        (
            raw_properties,
            variables_used,
            color_tokens,
            numeric_tokens,
            asset_dependencies,
        ) = resolve_css_class_properties(css_class, variable_registry)

        # Check raw properties
        assert raw_properties["color"] == "var(--primary)"
        assert raw_properties["border-radius"] == "4px"

        # Check extracted data
        assert "--primary" in variables_used
        assert "#1976D2" in color_tokens
        assert "4px" in numeric_tokens
        assert "test/icon" in asset_dependencies

    def test_resolve_class_with_multiple_values(self):
        """Test resolving class with multi-value properties."""
        css_class = CSSClass(
            name=".test-class",
            stylesheet="TestSheet",
            bundle="test.bundle",
            raw_properties={
                "padding": "6px 10px",
            },
            first_seen="2026.1.0",
            last_seen="2026.4.0",
        )

        (
            raw_properties,
            variables_used,
            color_tokens,
            numeric_tokens,
            asset_dependencies,
        ) = resolve_css_class_properties(css_class, {})

        assert raw_properties["padding"] == "6px 10px"
        assert "6px" in numeric_tokens
        assert "10px" in numeric_tokens

    def test_resolve_class_with_no_variables(self):
        """Test resolving class without any variables."""
        css_class = CSSClass(
            name=".test-class",
            stylesheet="TestSheet",
            bundle="test.bundle",
            raw_properties={
                "color": "#FFFFFF",
            },
            first_seen="2026.1.0",
            last_seen="2026.4.0",
        )

        (
            raw_properties,
            variables_used,
            color_tokens,
            numeric_tokens,
            asset_dependencies,
        ) = resolve_css_class_properties(css_class, {})

        assert len(variables_used) == 0
        assert raw_properties["color"] == "#FFFFFF"
        assert "#FFFFFF" in color_tokens

    def test_extract_variable_references(self):
        """Test extracting variable references."""
        resolver = CSSResolver()

        refs = resolver.extract_variable_references("var(--primary) solid var(--border)")

        assert "--primary" in refs
        assert "--border" in refs
        assert len(refs) == 2
