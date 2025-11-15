"""
Test catalogue models.
"""

from fm_skin_builder.core.catalogue.models import (
    AssetStatus,
    CatalogueMetadata,
    CSSVariable,
    CSSValueDefinition,
    CSSClass,
    CSSProperty,
    Sprite,
    Texture,
    Font,
)


def test_asset_status_enum():
    """Test AssetStatus enum values."""
    assert AssetStatus.ACTIVE == "active"
    assert AssetStatus.REMOVED == "removed"
    assert AssetStatus.MODIFIED == "modified"


def test_css_value_definition():
    """Test CSSValueDefinition model."""
    val = CSSValueDefinition(
        value_type=4,
        index=10,
        resolved_value="#1976d2",
        raw_value={"r": 0.098, "g": 0.463, "b": 0.824, "a": 1.0},
    )
    assert val.value_type == 4
    assert val.index == 10
    assert val.resolved_value == "#1976d2"
    assert str(val) == "#1976d2"


def test_css_property():
    """Test CSSProperty model."""
    val = CSSValueDefinition(value_type=4, index=10, resolved_value="#1976d2")
    prop = CSSProperty(name="background-color", values=[val])

    assert prop.name == "background-color"
    assert len(prop.values) == 1
    assert prop.css_notation == "background-color: #1976d2;"


def test_css_variable():
    """Test CSSVariable model."""
    val = CSSValueDefinition(value_type=4, index=10, resolved_value="#1976d2")
    var = CSSVariable(
        name="--primary-color",
        stylesheet="FMColours",
        bundle="skins.bundle",
        property_name="background-color",
        rule_index=5,
        values=[val],
        colors=["#1976d2"],
        first_seen="2026.1.0",
        last_seen="2026.4.0",
    )

    assert var.name == "--primary-color"
    assert var.stylesheet == "FMColours"
    assert var.colors == ["#1976d2"]
    assert var.status == AssetStatus.ACTIVE


def test_css_class():
    """Test CSSClass model."""
    val = CSSValueDefinition(value_type=4, index=10, resolved_value="#1976d2")
    prop = CSSProperty(name="background-color", values=[val])

    cls = CSSClass(
        name=".button-primary",
        stylesheet="FMColours",
        bundle="skins.bundle",
        properties=[prop],
        variables_used=["--primary-color"],
        tags=["button", "primary"],
        first_seen="2026.1.0",
        last_seen="2026.4.0",
    )

    assert cls.name == ".button-primary"
    assert len(cls.properties) == 1
    assert "button" in cls.tags


def test_sprite():
    """Test Sprite model."""
    sprite = Sprite(
        name="icon_player",
        aliases=["icon_player_16", "icon_player_24"],
        has_vertex_data=False,
        content_hash="abc123",
        thumbnail_path="thumbnails/sprites/abc123.webp",
        width=32,
        height=32,
        dominant_colors=["#1976d2", "#ffffff"],
        tags=["icon", "player"],
        bundles=["skins.bundle"],
        first_seen="2026.1.0",
        last_seen="2026.4.0",
    )

    assert sprite.name == "icon_player"
    assert len(sprite.aliases) == 2
    assert sprite.width == 32
    assert len(sprite.dominant_colors) == 2


def test_texture():
    """Test Texture model."""
    texture = Texture(
        name="bg_grass",
        content_hash="def456",
        thumbnail_path="thumbnails/textures/def456.webp",
        type="background",
        width=1024,
        height=1024,
        dominant_colors=["#00ff00"],
        tags=["background", "grass"],
        bundles=["skins.bundle"],
        first_seen="2026.1.0",
        last_seen="2026.4.0",
    )

    assert texture.name == "bg_grass"
    assert texture.type == "background"
    assert texture.width == 1024


def test_font():
    """Test Font model."""
    font = Font(
        name="Roboto-Regular",
        bundles=["fonts.bundle"],
        tags=["font", "roboto"],
        first_seen="2026.1.0",
        last_seen="2026.4.0",
    )

    assert font.name == "Roboto-Regular"
    assert "font" in font.tags


def test_catalogue_metadata():
    """Test CatalogueMetadata model."""
    metadata = CatalogueMetadata(
        fm_version="2026.4.0",
        bundles_scanned=["skins.bundle", "fonts.bundle"],
        total_assets={
            "sprites": 100,
            "textures": 50,
            "fonts": 5,
            "css_variables": 200,
        },
    )

    assert metadata.fm_version == "2026.4.0"
    assert metadata.schema_version == "2.1.0"
    assert len(metadata.bundles_scanned) == 2
    assert metadata.total_assets["sprites"] == 100


def test_json_serialization():
    """Test that models can be serialized to JSON."""
    import json

    metadata = CatalogueMetadata(
        fm_version="2026.4.0",
        bundles_scanned=["skins.bundle"],
        total_assets={"sprites": 1},
    )

    json_data = metadata.model_dump(mode="json")
    json_str = json.dumps(json_data)

    assert isinstance(json_str, str)
    assert "2026.4.0" in json_str
