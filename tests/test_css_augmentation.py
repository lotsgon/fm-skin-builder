"""Tests for CSS augmentation features (Phase 3)."""

from types import SimpleNamespace


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


class TestNewCssSelectors:
    """Test injecting new CSS selectors that don't exist in the stylesheet."""

    def test_add_new_class_selector_with_color(self):
        """Test adding a new class selector with a color property."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        unmatched_selectors = {(".button", "color")}
        selector_overrides = {(".button", "color"): "#FF0000"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_selectors(
            data, unmatched_selectors, selector_overrides, "test.uss"
        )

        assert count == 1
        assert len(data.colors) == 1
        assert len(data.m_Rules) == 1
        assert len(data.m_ComplexSelectors) == 1

        # Check rule
        rule = data.m_Rules[0]
        props = getattr(rule, "m_Properties")
        assert len(props) == 1
        assert getattr(props[0], "m_Name") == "color"

        # Check ComplexSelector
        complex_sel = data.m_ComplexSelectors[0]
        assert getattr(complex_sel, "ruleIndex") == 0

    def test_add_new_class_selector_with_float(self):
        """Test adding a new class selector with a float property."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        unmatched_selectors = {(".button", "font-size")}
        selector_overrides = {(".button", "font-size"): "16px"}

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_selectors(
            data, unmatched_selectors, selector_overrides, "test.uss"
        )

        assert count == 1
        assert len(data.floats) == 1
        assert data.floats[0] == 16.0

    def test_add_multiple_properties_to_same_selector(self):
        """Test adding multiple properties to the same new selector."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        unmatched_selectors = {
            (".button", "color"),
            (".button", "font-size"),
            (".button", "visibility"),
        }
        selector_overrides = {
            (".button", "color"): "#FF0000",
            (".button", "font-size"): "16px",
            (".button", "visibility"): "visible",
        }

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_selectors(
            data, unmatched_selectors, selector_overrides, "test.uss"
        )

        assert count == 3
        # Only one rule and one complex selector for all properties
        assert len(data.m_Rules) == 1
        assert len(data.m_ComplexSelectors) == 1

        # Rule should have 3 properties
        rule = data.m_Rules[0]
        props = getattr(rule, "m_Properties")
        assert len(props) == 3

        prop_names = [getattr(p, "m_Name") for p in props]
        assert "color" in prop_names
        assert "font-size" in prop_names
        assert "visibility" in prop_names

    def test_add_multiple_different_selectors(self):
        """Test adding multiple different selectors."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        unmatched_selectors = {
            (".button", "color"),
            (".title", "font-size"),
            ("#myid", "opacity"),
        }
        selector_overrides = {
            (".button", "color"): "#FF0000",
            (".title", "font-size"): "24px",
            ("#myid", "opacity"): "0.9",
        }

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_selectors(
            data, unmatched_selectors, selector_overrides, "test.uss"
        )

        assert count == 3
        # Three rules and three complex selectors (one per selector)
        assert len(data.m_Rules) == 3
        assert len(data.m_ComplexSelectors) == 3

    def test_parse_class_selector(self):
        """Test parsing of class selector (.button)."""
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        part = patcher._parse_selector_to_part(".button", [])

        assert getattr(part, "m_Type") == 3  # Class type
        assert getattr(part, "m_Value") == "button"  # Without dot

    def test_parse_id_selector(self):
        """Test parsing of ID selector (#myid)."""
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        part = patcher._parse_selector_to_part("#myid", [])

        assert getattr(part, "m_Type") == 2  # ID type
        assert getattr(part, "m_Value") == "myid"  # Without #

    def test_parse_element_selector(self):
        """Test parsing of element selector (Label)."""
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        part = patcher._parse_selector_to_part("Label", [])

        assert getattr(part, "m_Type") == 1  # Element type
        assert getattr(part, "m_Value") == "Label"

    def test_parse_pseudo_selector(self):
        """Test parsing of pseudo-class selector (:hover)."""
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        part = patcher._parse_selector_to_part(":hover", [])

        assert getattr(part, "m_Type") == 4  # Pseudo type
        assert getattr(part, "m_Value") == "hover"  # Without :

    def test_create_complex_selector(self):
        """Test creating a ComplexSelector structure."""
        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        complex_sel = patcher._create_complex_selector(".button", 5, [])

        assert getattr(complex_sel, "ruleIndex") == 5

        selectors = getattr(complex_sel, "m_Selectors")
        assert len(selectors) == 1

        simple_sel = selectors[0]
        parts = getattr(simple_sel, "m_Parts")
        assert len(parts) == 1

        part = parts[0]
        assert getattr(part, "m_Type") == 3  # Class
        assert getattr(part, "m_Value") == "button"

    def test_no_selectors_to_add(self):
        """Test when there are no unmatched selectors."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        count = patcher._add_new_css_selectors(data, set(), {}, "test.uss")

        assert count == 0
        assert len(data.m_Rules) == 0
        assert len(data.m_ComplexSelectors) == 0
