"""
Test font format detection and validation.
"""

import pytest
from pathlib import Path
from fm_skin_builder.core.font_swap_service import FontSwapService, FontSwapOptions


def test_detect_ttf_format():
    """Test TTF format detection."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # TrueType 1.0 magic
    ttf_bytes_v1 = b"\x00\x01\x00\x00" + b"\x00" * 100
    assert service._detect_font_format_from_bytes(ttf_bytes_v1) == "TTF"

    # TrueType Mac magic
    ttf_bytes_mac = b"true" + b"\x00" * 100
    assert service._detect_font_format_from_bytes(ttf_bytes_mac) == "TTF"


def test_detect_otf_format():
    """Test OTF format detection."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # OpenType with CFF
    otf_bytes = b"OTTO" + b"\x00" * 100
    assert service._detect_font_format_from_bytes(otf_bytes) == "OTF"


def test_detect_unknown_format():
    """Test unknown format detection."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # Invalid magic bytes
    invalid_bytes = b"ABCD" + b"\x00" * 100
    assert service._detect_font_format_from_bytes(invalid_bytes) == "UNKNOWN"

    # Too short
    short_bytes = b"AB"
    assert service._detect_font_format_from_bytes(short_bytes) == "UNKNOWN"


def test_detect_font_format_from_file(tmp_path):
    """Test format detection from file."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # Create TTF file
    ttf_file = tmp_path / "test.ttf"
    ttf_file.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 100)
    assert service._detect_font_format_from_file(ttf_file) == "TTF"

    # Create OTF file
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)
    assert service._detect_font_format_from_file(otf_file) == "OTF"


def test_validate_format_mismatch(tmp_path):
    """Test that format mismatch is detected during validation."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # Create an OTF file
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)

    # Validate with TTF expected - should fail
    error = service._validate_font_file(otf_file, original_format="TTF")
    assert error is not None
    assert "Format mismatch" in error
    assert "TTF" in error
    assert "OTF" in error

    # Validate with OTF expected - should pass
    error = service._validate_font_file(otf_file, original_format="OTF")
    assert error is None


def test_validate_matching_format(tmp_path):
    """Test that matching formats pass validation."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # TTF with TTF expected
    ttf_file = tmp_path / "test.ttf"
    ttf_file.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 100)
    error = service._validate_font_file(ttf_file, original_format="TTF")
    assert error is None

    # OTF with OTF expected
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)
    error = service._validate_font_file(otf_file, original_format="OTF")
    assert error is None


def test_validate_no_original_format(tmp_path):
    """Test validation when original format is unknown."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # Should not fail if we don't know original format
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)
    error = service._validate_font_file(otf_file, original_format=None)
    assert error is None


def test_validate_invalid_magic_bytes(tmp_path):
    """Test that invalid magic bytes are rejected."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], dry_run=False))

    # Create file with invalid magic bytes
    invalid_file = tmp_path / "test.ttf"
    invalid_file.write_bytes(b"ABCD" + b"\x00" * 100)

    error = service._validate_font_file(invalid_file, original_format=None)
    assert error is not None
    assert "unable to detect" in error.lower() or "invalid magic" in error.lower()
