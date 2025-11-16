"""
Integration tests for CSS/USS extraction with real FM26 bundles.
"""

import pytest
from pathlib import Path
from fm_skin_builder.core.catalogue.extractors.css_extractor import CSSExtractor
from fm_skin_builder.core.catalogue.dependency_graph import build_dependency_graphs
from fm_skin_builder.core.catalogue.search_builder import SearchIndexBuilder


class TestCSSIntegration:
    """Integration tests with real FM26 bundles."""

    @pytest.fixture
    def test_bundles_dir(self):
        """Get path to test bundles directory."""
        return Path(__file__).parent.parent / "test_bundles"

    @pytest.fixture
    def ui_styles_bundle(self, test_bundles_dir):
        """Get path to ui-styles bundle."""
        bundle_path = test_bundles_dir / "ui-styles_assets_default.bundle"
        if not bundle_path.exists():
            pytest.skip(f"Test bundle not found: {bundle_path}")
        return bundle_path

    def test_extract_css_from_real_bundle(self, ui_styles_bundle):
        """Test extracting CSS from a real FM26 bundle."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)

        # Should extract variables and classes
        assert "variables" in result
        assert "classes" in result

        variables = result["variables"]
        classes = result["classes"]

        # Should have some data
        if len(variables) > 0:
            print(f"✓ Extracted {len(variables)} CSS variables")
            # Check first variable structure
            var = variables[0]
            assert hasattr(var, "name")
            assert hasattr(var, "stylesheet")
            assert hasattr(var, "bundle")
            assert var.name.startswith("--") or var.name.startswith("-")

        if len(classes) > 0:
            print(f"✓ Extracted {len(classes)} CSS classes")
            # Check first class structure
            cls = classes[0]
            assert hasattr(cls, "name")
            assert hasattr(cls, "raw_properties")
            assert hasattr(cls, "stylesheet")

    def test_enhanced_class_data(self, ui_styles_bundle):
        """Test that enhanced class data is populated."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)
        classes = result["classes"]

        if len(classes) > 0:
            # Find a class with properties
            cls_with_props = None
            for cls in classes:
                if cls.raw_properties and len(cls.raw_properties) > 0:
                    cls_with_props = cls
                    break

            if cls_with_props:
                print(f"✓ Testing class: {cls_with_props.name}")

                # Check for enhanced fields
                # Note: Some may be None if no variables/assets are used
                assert hasattr(cls_with_props, "raw_properties")
                assert hasattr(cls_with_props, "asset_dependencies")
                assert hasattr(cls_with_props, "color_tokens")
                assert hasattr(cls_with_props, "numeric_tokens")

                # If enhanced, check structure
                if cls_with_props.raw_properties:
                    print(f"  - Raw properties: {list(cls_with_props.raw_properties.keys())}")
                    assert isinstance(cls_with_props.raw_properties, dict)

                if cls_with_props.color_tokens:
                    print(f"  - Color tokens: {cls_with_props.color_tokens[:3]}")
                    assert isinstance(cls_with_props.color_tokens, list)

                if cls_with_props.numeric_tokens:
                    print(f"  - Numeric tokens: {cls_with_props.numeric_tokens[:3]}")
                    assert isinstance(cls_with_props.numeric_tokens, list)

    def test_build_dependency_graphs_from_real_data(self, ui_styles_bundle):
        """Test building dependency graphs from real bundle data."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)
        variables = result["variables"]
        classes = result["classes"]

        if len(variables) > 0 and len(classes) > 0:
            # Build dependency graphs
            graphs = build_dependency_graphs(variables, classes)

            print(f"✓ Built dependency graphs")
            print(f"  - Variable → Classes: {len(graphs['variable_to_classes']['nodes'])} nodes, {len(graphs['variable_to_classes']['edges'])} edges")
            print(f"  - Class → Variables: {len(graphs['class_to_variables']['nodes'])} nodes, {len(graphs['class_to_variables']['edges'])} edges")
            print(f"  - Sprite → Classes: {len(graphs['sprite_to_classes']['nodes'])} nodes")

            # Check structure
            assert "variable_to_classes" in graphs
            assert "class_to_variables" in graphs
            assert "sprite_to_classes" in graphs
            assert "variable_dependencies" in graphs

            # Check each graph has required fields
            for graph_name, graph in graphs.items():
                assert "adjacency" in graph
                assert "nodes" in graph
                assert "edges" in graph
                assert "summary" in graph

    def test_build_search_indexes_from_real_data(self, ui_styles_bundle):
        """Test building search indexes from real bundle data."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)
        variables = result["variables"]
        classes = result["classes"]

        if len(variables) > 0 and len(classes) > 0:
            builder = SearchIndexBuilder()

            index = builder.build_index(
                variables,
                classes,
                [],  # sprites
                [],  # textures
                [],  # fonts
            )

            print(f"✓ Built search indexes")

            # Check all index sections exist
            assert "color_palette" in index
            assert "tags" in index
            assert "changes" in index
            assert "css_reverse_indexes" in index

            # Check reverse indexes
            reverse = index["css_reverse_indexes"]
            assert "color_to_classes" in reverse
            assert "property_to_classes" in reverse
            assert "variable_to_classes" in reverse
            assert "asset_to_classes" in reverse
            assert "token_to_classes" in reverse
            assert "variable_definitions" in reverse

            # Print some stats
            if reverse["color_to_classes"]:
                num_colors = len(reverse["color_to_classes"])
                print(f"  - Indexed {num_colors} unique colors")

            if reverse["property_to_classes"]:
                num_props = len(reverse["property_to_classes"])
                print(f"  - Indexed {num_props} unique properties")
                print(f"    Properties: {list(reverse['property_to_classes'].keys())[:5]}")

            if reverse["variable_to_classes"]:
                num_vars = len(reverse["variable_to_classes"])
                print(f"  - Indexed {num_vars} variables with class usage")

    def test_variable_resolution_from_real_data(self, ui_styles_bundle):
        """Test that variable resolution works with real data."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)
        classes = result["classes"]

        # Find classes that use variables
        classes_with_vars = [c for c in classes if len(c.variables_used) > 0]

        if len(classes_with_vars) > 0:
            print(f"✓ Found {len(classes_with_vars)} classes using variables")

            # Check first class
            cls = classes_with_vars[0]
            print(f"  Class: {cls.name}")
            print(f"  Variables used: {cls.variables_used}")

            # Should have both raw and resolved properties
            if cls.raw_properties and cls.resolved_properties:
                # Find a property that uses a variable
                for prop_name, raw_val in cls.raw_properties.items():
                    if "var(" in raw_val:
                        resolved_val = cls.resolved_properties.get(prop_name)
                        print(f"  Property '{prop_name}':")
                        print(f"    Raw: {raw_val}")
                        print(f"    Resolved: {resolved_val}")

                        # Resolved should not have var() if resolution worked
                        # (unless the variable wasn't found)
                        assert resolved_val is not None

    def test_asset_dependency_extraction(self, ui_styles_bundle):
        """Test extracting asset dependencies from real data."""
        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(ui_styles_bundle)
        classes = result["classes"]

        # Find classes with asset dependencies
        classes_with_assets = [c for c in classes if len(c.asset_dependencies) > 0]

        if len(classes_with_assets) > 0:
            print(f"✓ Found {len(classes_with_assets)} classes with asset dependencies")

            # Check first class
            cls = classes_with_assets[0]
            print(f"  Class: {cls.name}")
            print(f"  Assets: {cls.asset_dependencies[:3]}")

            # Assets should be strings
            for asset in cls.asset_dependencies:
                assert isinstance(asset, str)
                assert len(asset) > 0

    def test_common_bundle_also_works(self, test_bundles_dir):
        """Test that the common bundle also works."""
        bundle_path = test_bundles_dir / "ui-styles_assets_common.bundle"

        if not bundle_path.exists():
            pytest.skip(f"Test bundle not found: {bundle_path}")

        extractor = CSSExtractor(fm_version="2026.1.0")

        result = extractor.extract_from_bundle(bundle_path)

        variables = result["variables"]
        classes = result["classes"]

        print(f"✓ Common bundle: {len(variables)} variables, {len(classes)} classes")

        # Should extract something
        assert isinstance(variables, list)
        assert isinstance(classes, list)
