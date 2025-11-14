"""
Test font format conversion and permissive replacement.
"""

from fm_skin_builder.core.font_swap_service import FontSwapService, FontSwapOptions


def test_permissive_mode_allows_format_mismatch(tmp_path):
    """Test that permissive mode allows format mismatches (default behavior)."""
    service = FontSwapService(
        FontSwapOptions(
            includes=["fonts"],
            dry_run=False,
            auto_convert=False,
            strict_format=False,  # Permissive
        )
    )

    # Create OTF file
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)

    # Validate with TTF expected - should PASS with info message
    error = service._validate_font_file(otf_file, original_format="TTF")
    assert error is None  # No error in permissive mode


def test_strict_mode_blocks_format_mismatch(tmp_path):
    """Test that strict mode blocks format mismatches."""
    service = FontSwapService(
        FontSwapOptions(
            includes=["fonts"],
            dry_run=False,
            auto_convert=False,
            strict_format=True,  # Strict
        )
    )

    # Create OTF file
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)

    # Validate with TTF expected - should FAIL in strict mode
    error = service._validate_font_file(otf_file, original_format="TTF")
    assert error is not None
    assert "Format mismatch" in error
    assert "strict mode" in error


def test_auto_convert_enabled_by_default(tmp_path):
    """Test that auto-convert is True by default (CRITICAL for format matching)."""
    options = FontSwapOptions(includes=["fonts"], dry_run=False)
    assert options.auto_convert is True  # Auto-convert is now the default
    assert options.strict_format is False


def test_font_conversion_ttf_to_otf(tmp_path):
    """Test TTF to OTF conversion (requires fonttools)."""
    service = FontSwapService(
        FontSwapOptions(includes=["fonts"], dry_run=False, auto_convert=True)
    )

    # Create TTF file
    ttf_file = tmp_path / "test.ttf"
    ttf_file.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 100)

    # Try to convert to OTF (may not work without valid font)
    result = service._convert_font_format(ttf_file, "OTF")

    # If fonttools is available, we should get a result
    # If not, result will be None
    # Just test that it doesn't crash
    assert result is None or result.exists()


def test_font_conversion_otf_to_ttf(tmp_path):
    """Test OTF to TTF conversion (requires fonttools)."""
    service = FontSwapService(
        FontSwapOptions(includes=["fonts"], dry_run=False, auto_convert=True)
    )

    # Create OTF file
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)

    # Try to convert to TTF (may not work without valid font)
    result = service._convert_font_format(otf_file, "TTF")

    # Just test that it doesn't crash
    assert result is None or result.exists()


def test_permissive_vs_strict_behavior(tmp_path):
    """Compare permissive vs strict mode behavior."""
    # Create mismatched font
    otf_file = tmp_path / "test.otf"
    otf_file.write_bytes(b"OTTO" + b"\x00" * 100)

    # Permissive mode
    permissive = FontSwapService(
        FontSwapOptions(includes=["fonts"], strict_format=False)
    )
    assert permissive._validate_font_file(otf_file, "TTF") is None

    # Strict mode
    strict = FontSwapService(FontSwapOptions(includes=["fonts"], strict_format=True))
    assert strict._validate_font_file(otf_file, "TTF") is not None


def test_conversion_with_unknown_format(tmp_path):
    """Test that conversion fails gracefully with unknown format."""
    service = FontSwapService(FontSwapOptions(includes=["fonts"], auto_convert=True))

    test_file = tmp_path / "test.ttf"
    test_file.write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 100)

    # Try to convert to UNKNOWN - should fail gracefully
    result = service._convert_font_format(test_file, "UNKNOWN")
    assert result is None
