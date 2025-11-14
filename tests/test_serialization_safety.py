"""Tests to verify Unity serialization safety for Phase 3 features."""

from types import SimpleNamespace

from fm_skin_builder.core.css_patcher import CssPatcher
from fm_skin_builder.core.css_sources import CollectedCss


class TestSerializationSafety:
    """Verify that Phase 3 features don't cause serialization issues."""

    def test_array_indices_are_unique_within_stylesheet(self):
        """Verify that array indices are always unique within a stylesheet."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", ["existing1", "existing2"])
        setattr(data, "floats", [1.0, 2.0, 3.0])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        # Add new variables
        css_vars = {
            "--new-var1": "16px",
            "--new-var2": "bold",
            "--new-var3": "#FF0000",
        }

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        patcher._add_new_css_variables(data, set(css_vars.keys()), css_vars, "test.uss")

        # Verify floats array has unique indices
        assert len(data.floats) == 4  # 3 existing + 1 new (16px)
        assert data.floats[0] == 1.0  # Existing preserved
        assert data.floats[1] == 2.0  # Existing preserved
        assert data.floats[2] == 3.0  # Existing preserved
        assert data.floats[3] == 16.0  # New value appended

        # Verify strings array has unique indices
        assert len(data.strings) == 3  # 2 existing + 1 new (bold)
        assert data.strings[0] == "existing1"  # Existing preserved
        assert data.strings[1] == "existing2"  # Existing preserved
        assert data.strings[2] == "bold"  # New value appended

        # Verify colors array has unique indices
        assert len(data.colors) == 1  # 0 existing + 1 new (#FF0000)

        # Check that properties reference correct indices
        root_rule = data.m_Rules[0]
        props = getattr(root_rule, "m_Properties")

        # Find the float property (--new-var1)
        float_prop = next(p for p in props if getattr(p, "m_Name") == "--new-var1")
        float_val = getattr(float_prop, "m_Values")[0]
        assert getattr(float_val, "valueIndex") == 3  # Points to floats[3]

        # Find the keyword property (--new-var2)
        keyword_prop = next(p for p in props if getattr(p, "m_Name") == "--new-var2")
        keyword_val = getattr(keyword_prop, "m_Values")[0]
        assert getattr(keyword_val, "valueIndex") == 2  # Points to strings[2]

        # Find the color property (--new-var3)
        color_prop = next(p for p in props if getattr(p, "m_Name") == "--new-var3")
        color_val = getattr(color_prop, "m_Values")[0]
        assert getattr(color_val, "valueIndex") == 0  # Points to colors[0]

    def test_multiple_bundles_independent_arrays(self):
        """Verify that modifications to different stylesheets are independent."""
        # Simulate Bundle 1
        data1 = SimpleNamespace()
        setattr(data1, "colors", [])
        setattr(data1, "strings", [])
        setattr(data1, "floats", [])
        setattr(data1, "m_Rules", [])
        setattr(data1, "m_ComplexSelectors", [])

        # Simulate Bundle 2
        data2 = SimpleNamespace()
        setattr(data2, "colors", [])
        setattr(data2, "strings", [])
        setattr(data2, "floats", [])
        setattr(data2, "m_Rules", [])
        setattr(data2, "m_ComplexSelectors", [])

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        # Add same variable to both bundles
        css_vars = {"--button-size": "16px"}

        patcher._add_new_css_variables(
            data1, set(css_vars.keys()), css_vars, "bundle1.uss"
        )
        patcher._add_new_css_variables(
            data2, set(css_vars.keys()), css_vars, "bundle2.uss"
        )

        # Both should have index 0 in their own float arrays (no conflict)
        assert len(data1.floats) == 1
        assert data1.floats[0] == 16.0

        assert len(data2.floats) == 1
        assert data2.floats[0] == 16.0

        # Indices are local to each StyleSheet - no conflict possible
        prop1 = getattr(data1.m_Rules[0], "m_Properties")[0]
        val1 = getattr(prop1, "m_Values")[0]
        assert getattr(val1, "valueIndex") == 0

        prop2 = getattr(data2.m_Rules[0], "m_Properties")[0]
        val2 = getattr(prop2, "m_Values")[0]
        assert getattr(val2, "valueIndex") == 0

        # Same index in different stylesheets is fine - they're independent

    def test_rules_and_selectors_are_embedded_data(self):
        """Verify that Rules and ComplexSelectors are data structures, not objects with PathIDs."""
        data = SimpleNamespace()
        setattr(data, "colors", [])
        setattr(data, "strings", [])
        setattr(data, "floats", [])
        setattr(data, "m_Rules", [])
        setattr(data, "m_ComplexSelectors", [])

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        unmatched_selectors = {(".button", "color")}
        selector_overrides = {(".button", "color"): "#FF0000"}

        patcher._add_new_css_selectors(
            data, unmatched_selectors, selector_overrides, "test.uss"
        )

        # Check that created structures don't have PathIDs
        new_rule = data.m_Rules[0]
        assert not hasattr(new_rule, "m_PathID")  # It's data, not a Unity Object

        new_complex_sel = data.m_ComplexSelectors[0]
        assert not hasattr(new_complex_sel, "m_PathID")  # It's data, not a Unity Object

        # They're just SimpleNamespace objects with the necessary fields
        assert hasattr(new_rule, "m_Properties")
        assert hasattr(new_complex_sel, "ruleIndex")

    def test_no_cross_bundle_id_pollution(self):
        """Verify that adding variables/selectors doesn't affect other bundles."""
        # This test verifies the conceptual independence
        # In practice, each bundle is processed separately and saved independently

        bundle_a_data = SimpleNamespace()
        setattr(bundle_a_data, "colors", [])
        setattr(bundle_a_data, "strings", [])
        setattr(bundle_a_data, "floats", [])
        setattr(bundle_a_data, "m_Rules", [])
        setattr(bundle_a_data, "m_ComplexSelectors", [])

        bundle_b_data = SimpleNamespace()
        setattr(bundle_b_data, "colors", [])
        setattr(bundle_b_data, "strings", ["pre-existing"])
        setattr(bundle_b_data, "floats", [10.0])
        setattr(bundle_b_data, "m_Rules", [])
        setattr(bundle_b_data, "m_ComplexSelectors", [])

        css_data = CollectedCss(global_vars={}, global_selectors={})
        patcher = CssPatcher(css_data)

        # Add to bundle A
        patcher._add_new_css_variables(
            bundle_a_data, {"--var-a"}, {"--var-a": "20px"}, "bundle_a.uss"
        )

        # Add to bundle B
        patcher._add_new_css_variables(
            bundle_b_data, {"--var-b"}, {"--var-b": "30px"}, "bundle_b.uss"
        )

        # Bundle A should have its own independent arrays
        assert len(bundle_a_data.floats) == 1
        assert bundle_a_data.floats[0] == 20.0

        # Bundle B should have its own independent arrays (with pre-existing data preserved)
        assert len(bundle_b_data.strings) == 1  # Pre-existing still there
        assert bundle_b_data.strings[0] == "pre-existing"
        assert len(bundle_b_data.floats) == 2  # Pre-existing + new
        assert bundle_b_data.floats[0] == 10.0  # Pre-existing
        assert bundle_b_data.floats[1] == 30.0  # New

        # No cross-contamination between bundles
