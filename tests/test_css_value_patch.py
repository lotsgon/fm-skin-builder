"""Tests for CSS value patching and tokenization."""

from fm_skin_builder.core.css_utils import (
    apply_value_patch_preserve,
    is_css_variable_reference,
    is_color_token,
    tokenize_css_value,
    safe_parse_float,
)


def test_tokenize_simple():
    """Test tokenization of simple space-separated values."""
    assert tokenize_css_value("1px solid #111111") == ["1px", "solid", "#111111"]
    assert tokenize_css_value("10px 20px 30px") == ["10px", "20px", "30px"]
    assert tokenize_css_value("#00ff00") == ["#00ff00"]


def test_tokenize_with_functions():
    """Test tokenization preserves function calls as single tokens."""
    assert tokenize_css_value("rgba(255, 0, 0, 0.5)") == ["rgba(255, 0, 0, 0.5)"]
    assert tokenize_css_value("1px solid rgba(255, 0, 0, 0.5)") == [
        "1px",
        "solid",
        "rgba(255, 0, 0, 0.5)",
    ]
    assert tokenize_css_value("var(--my-color)") == ["var(--my-color)"]


def test_is_css_variable_reference():
    """Test CSS variable detection."""
    assert is_css_variable_reference("--my-var")
    assert is_css_variable_reference("--layout-ui-tiles-interaction-border-default")
    assert is_css_variable_reference(
        "var(--my-var)"
    )  # var() function calls are also variable references
    assert not is_css_variable_reference("#ffffff")
    assert not is_css_variable_reference("10px")


def test_is_color_token():
    """Test color token detection."""
    assert is_color_token("#111111")
    assert is_color_token("#00ff00")
    assert is_color_token("#00ff00ff")  # With alpha
    assert is_color_token("rgba(255, 0, 0, 0.5)")
    assert is_color_token("rgb(255, 0, 0)")
    assert not is_color_token("1px")
    assert not is_color_token("solid")
    assert not is_color_token("--my-var")


def test_replace_color_in_triplet():
    """Test replacing color in a multi-value shorthand (e.g., border)."""
    original = "1px solid #111111"
    replacement = "#00ff00"
    result = apply_value_patch_preserve(original, replacement)
    assert result == "1px solid #00ff00"


def test_replace_color_in_border_with_rgba():
    """Test replacing color when original has rgba()."""
    original = "2px dashed rgba(0, 0, 0, 0.5)"
    replacement = "#ffffff"
    result = apply_value_patch_preserve(original, replacement)
    assert result == "2px dashed #ffffff"


def test_skip_variable_reference():
    """Test that CSS variable references are left untouched."""
    original = "var(--layout-ui-tiles-interaction-border-default)"
    replacement = "#ffffff"
    result = apply_value_patch_preserve(original, replacement)
    assert result == original


def test_skip_variable_in_multi_value():
    """Test that multi-value properties with variables are left untouched."""
    original = "1px solid var(--my-color)"
    replacement = "#ffffff"
    result = apply_value_patch_preserve(original, replacement)
    # Should be skipped because it contains a variable reference
    assert result == original


def test_preserve_non_color_triplet():
    """Test that non-color triplets are preserved when replacement isn't a color."""
    original = "10px 20px 30px"
    replacement = "5px"
    result = apply_value_patch_preserve(original, replacement)
    # Fallback behavior: keep original because replacement isn't a color
    assert result == original


def test_same_token_count_replacement():
    """Test direct replacement when token counts match."""
    original = "1px solid #111111"
    replacement = "2px dashed #222222"
    result = apply_value_patch_preserve(original, replacement)
    assert result == "2px dashed #222222"


def test_single_token_replacement():
    """Test single token replacement."""
    original = "#111111"
    replacement = "#00ff00"
    result = apply_value_patch_preserve(original, replacement)
    assert result == "#00ff00"


def test_preserve_when_no_color_token_and_replacement_is_color():
    """Test that we keep original if replacement is color but original has no color token."""
    original = "10px 20px"
    replacement = "#ff0000"
    result = apply_value_patch_preserve(original, replacement)
    # No color token in original, so can't replace - keep original
    assert result == original


# Tests for safe_parse_float (prevents 0.0 coercion)


def test_safe_parse_float_valid_numbers():
    """Test parsing valid numeric values."""
    assert safe_parse_float("8") == 8.0
    assert safe_parse_float("8.5") == 8.5
    assert safe_parse_float("8px") == 8.0
    assert safe_parse_float("8.5em") == 8.5
    assert safe_parse_float("-5.2") == -5.2
    assert safe_parse_float("+10.0") == 10.0
    assert safe_parse_float("1.5e2") == 150.0


def test_safe_parse_float_already_numeric():
    """Test that numeric types are handled correctly."""
    assert safe_parse_float(8) == 8.0
    assert safe_parse_float(8.5) == 8.5
    assert safe_parse_float(0) == 0.0  # Explicit zero is OK
    assert safe_parse_float(0.0) == 0.0


def test_safe_parse_float_invalid_returns_none():
    """Test that invalid inputs return None, NOT 0.0."""
    assert safe_parse_float("") is None
    assert safe_parse_float("abc") is None
    assert safe_parse_float("--my-var") is None
    assert safe_parse_float("var(--x)") is None
    assert safe_parse_float(None) is None


def test_safe_parse_float_with_default():
    """Test that default value is returned for invalid inputs."""
    assert safe_parse_float("", default=0.0) == 0.0
    assert safe_parse_float("invalid", default=-1.0) == -1.0
    assert safe_parse_float(None, default=100.0) == 100.0


def test_safe_parse_float_prevents_zero_coercion():
    """Critical test: ensure invalid values don't become 0.0."""
    # These should NOT return 0.0
    assert safe_parse_float("--border-radius-radius-8") is None
    assert safe_parse_float("--border-width-border-width-1") is None
    assert safe_parse_float("") is None

    # Only explicit zero should return 0.0
    assert safe_parse_float("0") == 0.0
    assert safe_parse_float("0.0") == 0.0
    assert safe_parse_float("0px") == 0.0
