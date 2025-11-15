"""
Test enhanced search builder functionality (schema 2.2.0+).
"""

import pytest
from fm_skin_builder.core.catalogue.search_builder import SearchIndexBuilder
from fm_skin_builder.core.catalogue.models import (
    CSSVariable,
    CSSClass,
    CSSValueDefinition,
    Sprite,
    Texture,
    Font,
)


class TestSearchIndexBuilderEnhanced:
    """Test enhanced search index building (reverse indexes)."""

    @pytest.fixture
    def sample_variables(self):
        """Create sample CSS variables."""
        return [
            CSSVariable(
                name="--primary",
                stylesheet="FMColours",
                bundle="test.bundle",
                property_name="--primary",
                rule_index=0,
                values=[CSSValueDefinition(value_type=4, index=0, resolved_value="#1976D2")],
                colors=["#1976D2"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSVariable(
                name="--secondary",
                stylesheet="FMColours",
                bundle="test.bundle",
                property_name="--secondary",
                rule_index=1,
                values=[CSSValueDefinition(value_type=4, index=1, resolved_value="#FFFFFF")],
                colors=["#FFFFFF"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

    @pytest.fixture
    def sample_classes(self):
        """Create sample CSS classes with enhanced data."""
        return [
            CSSClass(
                name=".btn-primary",
                stylesheet="FMButtons",
                bundle="test.bundle",
                properties=[],
                raw_properties={"color": "#FFFFFF", "background-color": "var(--primary)"},
                resolved_properties={"color": "#FFFFFF", "background-color": "#1976D2"},
                variables_used=["--primary"],
                color_tokens=["#FFFFFF", "#1976D2"],
                numeric_tokens=["4px", "10px"],
                asset_dependencies=["FMImages_1x/button_bg"],
                tags=["button", "primary"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSClass(
                name=".player-name",
                stylesheet="FMColours",
                bundle="test.bundle",
                properties=[],
                raw_properties={"color": "#FFFFFF", "border-radius": "4px"},
                resolved_properties={"color": "#FFFFFF", "border-radius": "4px"},
                variables_used=[],
                color_tokens=["#FFFFFF"],
                numeric_tokens=["4px"],
                asset_dependencies=["FMImages_1x/star_full"],
                tags=["player", "name"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSClass(
                name=".header-title",
                stylesheet="FMTypography",
                bundle="test.bundle",
                properties=[],
                raw_properties={"color": "var(--secondary)", "font-size": "16px"},
                resolved_properties={"color": "#FFFFFF", "font-size": "16px"},
                variables_used=["--secondary"],
                color_tokens=["#FFFFFF"],
                numeric_tokens=["16px"],
                asset_dependencies=[],
                tags=["header", "title"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

    def test_build_css_reverse_indexes(self, sample_classes, sample_variables):
        """Test building comprehensive reverse indexes."""
        builder = SearchIndexBuilder()

        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        assert "color_to_classes" in indexes
        assert "property_to_classes" in indexes
        assert "variable_to_classes" in indexes
        assert "asset_to_classes" in indexes
        assert "token_to_classes" in indexes
        assert "variable_definitions" in indexes

    def test_color_to_classes_index(self, sample_classes, sample_variables):
        """Test color → classes reverse index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        color_index = indexes["color_to_classes"]

        # All three classes use #FFFFFF
        assert "#FFFFFF" in color_index
        assert ".btn-primary" in color_index["#FFFFFF"]
        assert ".player-name" in color_index["#FFFFFF"]
        assert ".header-title" in color_index["#FFFFFF"]

        # Only btn-primary uses #1976D2 (resolved from --primary)
        assert "#1976D2" in color_index
        assert ".btn-primary" in color_index["#1976D2"]

    def test_property_to_classes_index(self, sample_classes, sample_variables):
        """Test property name → classes reverse index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        prop_index = indexes["property_to_classes"]

        # color property used by all three classes
        assert "color" in prop_index
        assert len(prop_index["color"]) == 3

        # border-radius only used by .player-name
        assert "border-radius" in prop_index
        assert ".player-name" in prop_index["border-radius"]

        # font-size only used by .header-title
        assert "font-size" in prop_index
        assert ".header-title" in prop_index["font-size"]

    def test_variable_to_classes_index(self, sample_classes, sample_variables):
        """Test variable → classes reverse index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        var_index = indexes["variable_to_classes"]

        # --primary used by .btn-primary
        assert "--primary" in var_index
        assert ".btn-primary" in var_index["--primary"]

        # --secondary used by .header-title
        assert "--secondary" in var_index
        assert ".header-title" in var_index["--secondary"]

    def test_asset_to_classes_index(self, sample_classes, sample_variables):
        """Test asset → classes reverse index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        asset_index = indexes["asset_to_classes"]

        # FMImages_1x/button_bg used by .btn-primary
        assert "FMImages_1x/button_bg" in asset_index
        assert ".btn-primary" in asset_index["FMImages_1x/button_bg"]

        # FMImages_1x/star_full used by .player-name
        assert "FMImages_1x/star_full" in asset_index
        assert ".player-name" in asset_index["FMImages_1x/star_full"]

    def test_token_to_classes_index(self, sample_classes, sample_variables):
        """Test numeric token → classes reverse index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        token_index = indexes["token_to_classes"]

        # 4px used by both .btn-primary and .player-name
        assert "4px" in token_index
        assert ".btn-primary" in token_index["4px"]
        assert ".player-name" in token_index["4px"]

        # 10px only used by .btn-primary
        assert "10px" in token_index
        assert ".btn-primary" in token_index["10px"]

        # 16px only used by .header-title
        assert "16px" in token_index
        assert ".header-title" in token_index["16px"]

    def test_variable_definitions_index(self, sample_classes, sample_variables):
        """Test variable definitions index."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes(sample_classes, sample_variables)

        var_defs = indexes["variable_definitions"]

        # Both variables should be tracked
        assert "--primary" in var_defs
        assert "--secondary" in var_defs

        # Check definition details
        primary_def = var_defs["--primary"][0]
        assert primary_def["stylesheet"] == "FMColours"
        assert primary_def["bundle"] == "test.bundle"

    def test_full_index_build(self, sample_variables, sample_classes):
        """Test building full search index with reverse indexes."""
        builder = SearchIndexBuilder()

        sprites = []
        textures = []
        fonts = []

        index = builder.build_index(
            sample_variables,
            sample_classes,
            sprites,
            textures,
            fonts,
        )

        # Check that all sections exist
        assert "color_palette" in index
        assert "tags" in index
        assert "changes" in index
        assert "css_reverse_indexes" in index

        # Check reverse indexes section
        reverse = index["css_reverse_indexes"]
        assert "color_to_classes" in reverse
        assert "property_to_classes" in reverse
        assert "variable_to_classes" in reverse
        assert "asset_to_classes" in reverse
        assert "token_to_classes" in reverse

    def test_empty_classes(self, sample_variables):
        """Test building indexes with no CSS classes."""
        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes([], sample_variables)

        # Should have empty indexes
        assert len(indexes["color_to_classes"]) == 0
        assert len(indexes["property_to_classes"]) == 0
        assert len(indexes["variable_to_classes"]) == 0
        assert len(indexes["asset_to_classes"]) == 0

        # But should still have variable definitions
        assert len(indexes["variable_definitions"]) == 2

    def test_class_without_enhanced_data(self, sample_variables):
        """Test handling classes without enhanced data (backward compatibility)."""
        # Create a class without the new enhanced fields
        basic_class = CSSClass(
            name=".basic-class",
            stylesheet="Test",
            bundle="test.bundle",
            properties=[],
            first_seen="2026.1.0",
            last_seen="2026.4.0",
        )

        builder = SearchIndexBuilder()
        indexes = builder._build_css_reverse_indexes([basic_class], sample_variables)

        # Should not crash, but will have minimal data
        assert "color_to_classes" in indexes
        # Class won't appear in color index since it has no color_tokens
        for colors in indexes["color_to_classes"].values():
            assert ".basic-class" not in colors
