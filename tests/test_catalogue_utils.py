"""
Test catalogue utility functions.
"""

import pytest

from fm_skin_builder.core.catalogue.auto_tagger import generate_tags, generate_css_tags
from fm_skin_builder.core.catalogue.color_search import hex_to_rgb, rgb_to_lab, color_distance
from fm_skin_builder.core.catalogue.content_hasher import compute_hash
from fm_skin_builder.core.catalogue.deduplicator import deduplicate_by_filename


def test_generate_tags():
    """Test tag generation from asset names."""
    tags = generate_tags("icon_player_primary_16")
    assert "icon" in tags
    assert "player" in tags
    assert "primary" in tags
    # "16" should be filtered out
    assert "16" not in tags


def test_generate_css_tags():
    """Test tag generation from CSS selectors."""
    tags = generate_css_tags(".button-primary")
    assert "button" in tags
    assert "primary" in tags


def test_hex_to_rgb():
    """Test hex to RGB conversion."""
    r, g, b = hex_to_rgb("#1976d2")
    assert r == 25
    assert g == 118
    assert b == 210

    # Test 3-character hex
    r, g, b = hex_to_rgb("#fff")
    assert r == 255
    assert g == 255
    assert b == 255


def test_rgb_to_lab():
    """Test RGB to LAB conversion."""
    L, a, b = rgb_to_lab(255, 255, 255)
    assert L > 90  # White should have high L value

    L, a, b = rgb_to_lab(0, 0, 0)
    assert L < 10  # Black should have low L value


def test_color_distance():
    """Test perceptual color distance calculation."""
    # Same color = 0 distance
    distance = color_distance("#1976d2", "#1976d2")
    assert distance == 0.0

    # Similar blues = small distance
    distance = color_distance("#1976d2", "#2196f3")
    assert distance < 20.0

    # Very different colors = large distance
    distance = color_distance("#1976d2", "#ff0000")
    assert distance > 50.0


def test_compute_hash():
    """Test hash computation."""
    hash1 = compute_hash(b"test data")
    hash2 = compute_hash(b"test data")
    hash3 = compute_hash(b"different data")

    # Same data = same hash
    assert hash1 == hash2

    # Different data = different hash
    assert hash1 != hash3

    # Hash should be hex string
    assert len(hash1) == 64  # SHA256 = 64 hex chars


def test_deduplicate_by_filename():
    """Test filename deduplication."""
    # Test size variants
    result = deduplicate_by_filename([
        "icon_player_16",
        "icon_player_24",
        "icon_player_32",
    ])

    assert "icon_player_16" in result
    aliases = result["icon_player_16"]
    assert "icon_player_24" in aliases
    assert "icon_player_32" in aliases

    # Test no duplicates
    result = deduplicate_by_filename(["icon_unique"])
    assert "icon_unique" in result
    assert result["icon_unique"] == []

    # Test @2x variants
    result = deduplicate_by_filename([
        "bg_grass",
        "bg_grass@2x",
    ])
    assert "bg_grass" in result
    assert "bg_grass@2x" in result["bg_grass"]
