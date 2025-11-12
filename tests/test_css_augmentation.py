"""Tests for CSS augmentation features (Phase 3)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fm_skin_builder.core.css_patcher import CssPatcher
from fm_skin_builder.core.css_sources import CollectedCss


class TestNewCssVariables:
    """Test adding new CSS variables that don't exist in the stylesheet."""

    def test_add_new_float_variable(self):
        """Test adding a new float CSS variable."""
        # Create mock stylesheet data
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        # Create CSS variables
        css_vars = {"--new-font-size": "16px"}

        # Create patcher
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        # Add new variables
        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 1
        assert len(data.m_Rules) == 1  # Root rule created
        assert len(data.floats) == 1  # Float added
        assert data.floats[0] == 16.0

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        assert len(props) == 1

        prop = props[0]
        assert getattr(prop, "m_Name") == "--new-font-size"
        values = getattr(prop, "m_Values")
        assert len(values) == 1
        assert getattr(values[0], "m_ValueType") == 2  # Float type
        assert getattr(values[0], "valueIndex") == 0

    def test_add_new_color_variable(self):
        """Test adding a new color CSS variable."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {"--new-color": "#FF0000"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 1
        assert len(data.colors) == 1  # Color added
        assert len(data.m_Rules) == 1

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        prop = props[0]
        assert getattr(prop, "m_Name") == "--new-color"
        values = getattr(prop, "m_Values")
        assert getattr(values[0], "m_ValueType") == 4  # Color type

    def test_add_new_keyword_variable(self):
        """Test adding a new keyword CSS variable."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {"--new-visibility": "hidden"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 1
        assert len(data.strings) == 1  # Keyword added to strings
        assert data.strings[0] == "hidden"

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        prop = props[0]
        assert getattr(prop, "m_Name") == "--new-visibility"
        values = getattr(prop, "m_Values")
        assert getattr(values[0], "m_ValueType") == 8  # Keyword type

    def test_add_new_resource_variable(self):
        """Test adding a new resource CSS variable."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {"--new-font": "url('resource://fonts/MyFont')"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 1
        assert len(data.strings) == 1  # Resource path added to strings
        assert data.strings[0] == "resource://fonts/MyFont"

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        prop = props[0]
        assert getattr(prop, "m_Name") == "--new-font"
        values = getattr(prop, "m_Values")
        assert getattr(values[0], "m_ValueType") == 7  # Resource type

    def test_add_multiple_new_variables(self):
        """Test adding multiple new CSS variables at once."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {
            "--new-size": "20px",
            "--new-color": "#00FF00",
            "--new-visibility": "visible",
            "--new-font": "url('resource://fonts/Bold')",
        }

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 4
        assert len(data.floats) == 1  # --new-size
        assert len(data.colors) == 1  # --new-color
        assert len(data.strings) == 2  # --new-visibility, --new-font

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        assert len(props) == 4

        # Check all variables were added
        var_names = [getattr(p, "m_Name") for p in props]
        assert "--new-color" in var_names
        assert "--new-font" in var_names
        assert "--new-size" in var_names
        assert "--new-visibility" in var_names

    def test_add_variables_to_existing_root_rule(self):
        """Test adding variables to an existing root rule."""
        # Create existing root rule
        existing_root = SimpleNamespace()
        setattr(existing_root, "m_Properties", [])
        setattr(existing_root, "line", -1)

        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [existing_root])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {"--new-size": "12px"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 1
        # Should use existing root rule, not create new one
        assert len(data.m_Rules) == 1
        assert data.m_Rules[0] is existing_root

        props = getattr(existing_root, "m_Properties")
        assert len(props) == 1

    def test_no_variables_to_add(self):
        """Test when there are no unmatched variables."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(data, set(), {}, "test.uss")

        assert count == 0
        assert len(data.m_Rules) == 0  # No root rule created

    def test_sorted_variable_names(self):
        """Test that variables are added in sorted order."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_vars = {
            "--zebra": "10px",
            "--alpha": "20px",
            "--middle": "30px",
        }

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_variables(
            data, set(css_vars.keys()), css_vars, "test.uss"
        )

        assert count == 3

        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")
        var_names = [getattr(p, "m_Name") for p in props]

        # Should be sorted alphabetically
        assert var_names == ["--alpha", "--middle", "--zebra"]
