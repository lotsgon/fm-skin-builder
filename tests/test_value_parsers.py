"""Tests for CSS value parsers."""

import pytest
from fm_skin_builder.core.value_parsers import (
    parse_float_value,
    parse_keyword_value,
    parse_resource_value,
    parse_css_value,
    parse_multi_value,
    expand_shorthand_box,
    FloatValue,
    KeywordValue,
    ResourceValue,
    CssValueType,
)


class TestFloatValueParsing:
    """Test parsing of float values with units."""

    def test_parse_simple_integer(self):
        result = parse_float_value("42")
        assert result is not None
        assert result.value == 42.0
        assert result.unit is None

    def test_parse_simple_float(self):
        result = parse_float_value("3.14")
        assert result is not None
        assert result.value == 3.14
        assert result.unit is None

    def test_parse_pixels(self):
        result = parse_float_value("12px")
        assert result is not None
        assert result.value == 12.0
        assert result.unit == "px"

    def test_parse_em(self):
        result = parse_float_value("1.5em")
        assert result is not None
        assert result.value == 1.5
        assert result.unit == "em"

    def test_parse_percentage(self):
        result = parse_float_value("100%")
        assert result is not None
        assert result.value == 100.0
        assert result.unit == "%"

    def test_parse_negative(self):
        result = parse_float_value("-10px")
        assert result is not None
        assert result.value == -10.0
        assert result.unit == "px"

    def test_parse_zero(self):
        result = parse_float_value("0")
        assert result is not None
        assert result.value == 0.0
        assert result.unit is None

    def test_parse_rem(self):
        result = parse_float_value("2rem")
        assert result is not None
        assert result.value == 2.0
        assert result.unit == "rem"

    def test_parse_invalid_unit(self):
        # Unknown units should be treated as unitless with a warning
        result = parse_float_value("10foo")
        assert result is not None
        assert result.value == 10.0
        assert result.unit is None  # Invalid unit stripped

    def test_parse_empty_string(self):
        result = parse_float_value("")
        assert result is None

    def test_parse_non_numeric(self):
        result = parse_float_value("abc")
        assert result is None


class TestKeywordValueParsing:
    """Test parsing of keyword/enum values."""

    def test_parse_visibility_keyword(self):
        result = parse_keyword_value("visible")
        assert result is not None
        assert result.keyword == "visible"

    def test_parse_hidden_keyword(self):
        result = parse_keyword_value("hidden")
        assert result is not None
        assert result.keyword == "hidden"

    def test_parse_bold_keyword(self):
        result = parse_keyword_value("bold")
        assert result is not None
        assert result.keyword == "bold"

    def test_parse_center_keyword(self):
        result = parse_keyword_value("center")
        assert result is not None
        assert result.keyword == "center"

    def test_parse_auto_keyword(self):
        result = parse_keyword_value("auto")
        assert result is not None
        assert result.keyword == "auto"

    def test_parse_unity_specific_keyword(self):
        result = parse_keyword_value("scale-and-crop")
        assert result is not None
        assert result.keyword == "scale-and-crop"

    def test_parse_uppercase_keyword(self):
        result = parse_keyword_value("BOLD")
        assert result is not None
        assert result.keyword == "bold"  # Normalized to lowercase

    def test_parse_unknown_keyword(self):
        # Unity-specific keywords with dashes should still parse
        result = parse_keyword_value("my-custom-value")
        assert result is not None
        assert result.keyword == "my-custom-value"

    def test_parse_empty_string(self):
        result = parse_keyword_value("")
        assert result is None

    def test_parse_invalid_keyword(self):
        # Keywords starting with numbers are invalid
        result = parse_keyword_value("123abc")
        assert result is None


class TestResourceValueParsing:
    """Test parsing of resource references."""

    def test_parse_resource_url_single_quotes(self):
        result = parse_resource_value("url('resource://fonts/MyFont')")
        assert result is not None
        assert result.path == "resource://fonts/MyFont"
        assert result.resource_type == "fonts"

    def test_parse_resource_url_double_quotes(self):
        result = parse_resource_value('url("resource://images/icon.png")')
        assert result is not None
        assert result.path == "resource://images/icon.png"
        assert result.resource_type == "images"

    def test_parse_resource_url_no_quotes(self):
        result = parse_resource_value("url(my-font)")
        assert result is not None
        assert result.path == "my-font"
        assert result.resource_type is None

    def test_parse_relative_path(self):
        result = parse_resource_value("url('path/to/file.png')")
        assert result is not None
        assert result.path == "path/to/file.png"
        assert result.resource_type is None

    def test_parse_empty_string(self):
        result = parse_resource_value("")
        assert result is None

    def test_parse_invalid_url(self):
        result = parse_resource_value("not-a-url")
        assert result is None

    def test_unity_path_conversion(self):
        result = parse_resource_value("url('my-font')")
        assert result is not None
        assert result.unity_path == "resource://my-font"


class TestGenericValueParsing:
    """Test the generic CSS value parser."""

    def test_parse_detects_float(self):
        result = parse_css_value("12px")
        assert result is not None
        assert result.value_type == CssValueType.FLOAT
        assert isinstance(result.value, FloatValue)
        assert result.value.value == 12.0
        assert result.value.unit == "px"

    def test_parse_detects_keyword(self):
        result = parse_css_value("bold")
        assert result is not None
        assert result.value_type == CssValueType.KEYWORD
        assert isinstance(result.value, KeywordValue)
        assert result.value.keyword == "bold"

    def test_parse_detects_resource(self):
        result = parse_css_value("url('resource://fonts/MyFont')")
        assert result is not None
        assert result.value_type == CssValueType.RESOURCE
        assert isinstance(result.value, ResourceValue)

    def test_parse_float_takes_precedence(self):
        # Numbers should be parsed as floats, not keywords
        result = parse_css_value("0")
        assert result is not None
        assert result.value_type == CssValueType.FLOAT

    def test_parse_empty_string(self):
        result = parse_css_value("")
        assert result is None

    def test_parse_with_property_context(self):
        result = parse_css_value("12px", property_name="font-size")
        assert result is not None
        assert result.value_type == CssValueType.FLOAT


class TestMultiValueParsing:
    """Test parsing of multi-value properties."""

    def test_parse_two_values(self):
        results = parse_multi_value("10px 20px")
        assert len(results) == 2
        assert results[0].value_type == CssValueType.FLOAT
        assert results[0].value.value == 10.0
        assert results[1].value.value == 20.0

    def test_parse_four_values(self):
        results = parse_multi_value("1px 2px 3px 4px")
        assert len(results) == 4
        assert all(r.value_type == CssValueType.FLOAT for r in results)
        assert [r.value.value for r in results] == [1.0, 2.0, 3.0, 4.0]

    def test_parse_mixed_units(self):
        results = parse_multi_value("1em 2px 3% 4")
        assert len(results) == 4
        assert results[0].value.unit == "em"
        assert results[1].value.unit == "px"
        assert results[2].value.unit == "%"
        assert results[3].value.unit is None

    def test_parse_empty_string(self):
        results = parse_multi_value("")
        assert len(results) == 0


class TestShorthandExpansion:
    """Test expansion of CSS shorthand properties."""

    def test_expand_one_value(self):
        values = parse_multi_value("10px")
        top, right, bottom, left = expand_shorthand_box(values)
        assert top.value.value == 10.0
        assert right.value.value == 10.0
        assert bottom.value.value == 10.0
        assert left.value.value == 10.0

    def test_expand_two_values(self):
        values = parse_multi_value("10px 20px")
        top, right, bottom, left = expand_shorthand_box(values)
        assert top.value.value == 10.0
        assert right.value.value == 20.0
        assert bottom.value.value == 10.0
        assert left.value.value == 20.0

    def test_expand_three_values(self):
        values = parse_multi_value("10px 20px 30px")
        top, right, bottom, left = expand_shorthand_box(values)
        assert top.value.value == 10.0
        assert right.value.value == 20.0
        assert bottom.value.value == 30.0
        assert left.value.value == 20.0

    def test_expand_four_values(self):
        values = parse_multi_value("10px 20px 30px 40px")
        top, right, bottom, left = expand_shorthand_box(values)
        assert top.value.value == 10.0
        assert right.value.value == 20.0
        assert bottom.value.value == 30.0
        assert left.value.value == 40.0

    def test_expand_invalid_count(self):
        with pytest.raises(ValueError):
            expand_shorthand_box([])
