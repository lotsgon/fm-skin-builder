"""
Test Dependency Graph Builder.
"""

import pytest
from fm_skin_builder.core.catalogue.dependency_graph import (
    DependencyGraphBuilder,
    build_dependency_graphs,
)
from fm_skin_builder.core.catalogue.models import (
    CSSVariable,
    CSSClass,
    CSSValueDefinition,
    CSSProperty,
)


class TestDependencyGraphBuilder:
    """Test DependencyGraphBuilder class."""

    @pytest.fixture
    def sample_variables(self):
        """Create sample CSS variables for testing."""
        return [
            CSSVariable(
                name="--primary",
                stylesheet="FMColours",
                bundle="test.bundle",
                property_name="--primary",
                rule_index=0,
                values=[CSSValueDefinition(value_type=4, index=0, resolved_value="#1976D2")],
                colors=["#1976D2"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSVariable(
                name="--secondary",
                stylesheet="FMColours",
                bundle="test.bundle",
                property_name="--secondary",
                rule_index=1,
                values=[CSSValueDefinition(value_type=4, index=1, resolved_value="#FFFFFF")],
                colors=["#FFFFFF"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSVariable(
                name="--accent",
                stylesheet="FMColours",
                bundle="test.bundle",
                property_name="--accent",
                rule_index=2,
                values=[CSSValueDefinition(value_type=10, index=2, resolved_value="var(--primary)")],
                colors=[],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

    @pytest.fixture
    def sample_classes(self):
        """Create sample CSS classes for testing."""
        return [
            CSSClass(
                name=".btn-primary",
                stylesheet="FMButtons",
                bundle="test.bundle",
                properties=[],
                variables_used=["--primary", "--secondary"],
                asset_dependencies=["FMImages_1x/button_bg"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSClass(
                name=".player-name",
                stylesheet="FMColours",
                bundle="test.bundle",
                properties=[],
                variables_used=["--primary"],
                asset_dependencies=["FMImages_1x/star_full"],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSClass(
                name=".header-title",
                stylesheet="FMTypography",
                bundle="test.bundle",
                properties=[],
                variables_used=["--secondary"],
                asset_dependencies=[],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

    def test_variable_to_classes_graph(self, sample_variables, sample_classes):
        """Test building Variable → Classes graph."""
        builder = DependencyGraphBuilder()

        graph = builder._build_variable_to_classes_graph(sample_variables, sample_classes)

        # Check adjacency list
        assert "--primary" in graph["adjacency"]
        assert ".btn-primary" in graph["adjacency"]["--primary"]
        assert ".player-name" in graph["adjacency"]["--primary"]

        # Check nodes
        assert len(graph["nodes"]) == 3
        primary_node = next(n for n in graph["nodes"] if n["id"] == "--primary")
        assert primary_node["type"] == "variable"
        assert primary_node["usage_count"] == 2

        # Check edges
        assert len(graph["edges"]) > 0
        edge = next((e for e in graph["edges"] if e["from"] == "--primary" and e["to"] == ".btn-primary"), None)
        assert edge is not None
        assert edge["type"] == "uses_variable"

        # Check summary
        assert "total_variables" in graph["summary"]
        assert "most_used_variables" in graph["summary"]

    def test_class_to_variables_graph(self, sample_classes):
        """Test building Class → Variables graph."""
        builder = DependencyGraphBuilder()

        graph = builder._build_class_to_variables_graph(sample_classes)

        # Check adjacency list
        assert ".btn-primary" in graph["adjacency"]
        assert "--primary" in graph["adjacency"][".btn-primary"]
        assert "--secondary" in graph["adjacency"][".btn-primary"]

        # Check nodes
        assert len(graph["nodes"]) == 3
        btn_node = next(n for n in graph["nodes"] if n["id"] == ".btn-primary")
        assert btn_node["type"] == "class"
        assert btn_node["variable_count"] == 2

        # Check edges
        edge = next((e for e in graph["edges"] if e["from"] == ".btn-primary" and e["to"] == "--primary"), None)
        assert edge is not None
        assert edge["type"] == "references_variable"

    def test_sprite_to_classes_graph(self, sample_classes):
        """Test building Sprite → Classes graph."""
        builder = DependencyGraphBuilder()

        graph = builder._build_sprite_to_classes_graph(sample_classes)

        # Check adjacency list
        assert "FMImages_1x/button_bg" in graph["adjacency"]
        assert ".btn-primary" in graph["adjacency"]["FMImages_1x/button_bg"]

        assert "FMImages_1x/star_full" in graph["adjacency"]
        assert ".player-name" in graph["adjacency"]["FMImages_1x/star_full"]

        # Check nodes
        assert len(graph["nodes"]) == 2
        sprite_node = next(n for n in graph["nodes"] if n["id"] == "FMImages_1x/button_bg")
        assert sprite_node["type"] == "asset"
        assert sprite_node["usage_count"] == 1

        # Check edges
        edge = next((e for e in graph["edges"] if e["from"] == "FMImages_1x/button_bg"), None)
        assert edge is not None
        assert edge["type"] == "used_by_class"

    def test_variable_dependencies_graph(self, sample_variables):
        """Test building Variable → Variable dependencies graph."""
        builder = DependencyGraphBuilder()

        graph = builder._build_variable_dependencies_graph(sample_variables)

        # Check that --accent depends on --primary
        assert "--accent" in graph["adjacency"]
        assert "--primary" in graph["adjacency"]["--accent"]

        # Check nodes
        assert len(graph["nodes"]) == 3

        # Check summary
        assert graph["summary"]["variables_with_dependencies"] > 0

    def test_build_all_graphs(self, sample_variables, sample_classes):
        """Test building all graphs at once."""
        builder = DependencyGraphBuilder()

        graphs = builder.build_graphs(sample_variables, sample_classes)

        assert "variable_to_classes" in graphs
        assert "class_to_variables" in graphs
        assert "sprite_to_classes" in graphs
        assert "variable_dependencies" in graphs

    def test_top_n_by_usage(self, sample_variables, sample_classes):
        """Test getting top N items by usage."""
        builder = DependencyGraphBuilder()

        adjacency = {
            "--primary": [".class1", ".class2", ".class3"],
            "--secondary": [".class1"],
            "--accent": [".class1", ".class2"],
        }

        top = builder._get_top_n_by_usage(adjacency, 2)

        assert len(top) == 2
        assert top[0]["name"] == "--primary"
        assert top[0]["count"] == 3

    def test_empty_graphs(self):
        """Test building graphs with empty data."""
        builder = DependencyGraphBuilder()

        graphs = builder.build_graphs([], [])

        assert graphs["variable_to_classes"]["adjacency"] == {}
        assert len(graphs["variable_to_classes"]["nodes"]) == 0
        assert len(graphs["variable_to_classes"]["edges"]) == 0

    def test_convenience_function(self, sample_variables, sample_classes):
        """Test the convenience function."""
        graphs = build_dependency_graphs(sample_variables, sample_classes)

        assert "variable_to_classes" in graphs
        assert "class_to_variables" in graphs
        assert "sprite_to_classes" in graphs
        assert "variable_dependencies" in graphs

    def test_circular_variable_dependency(self):
        """Test handling circular variable dependencies."""
        vars_with_circular = [
            CSSVariable(
                name="--var-a",
                stylesheet="Test",
                bundle="test.bundle",
                property_name="--var-a",
                rule_index=0,
                values=[CSSValueDefinition(value_type=10, index=0, resolved_value="var(--var-b)")],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
            CSSVariable(
                name="--var-b",
                stylesheet="Test",
                bundle="test.bundle",
                property_name="--var-b",
                rule_index=1,
                values=[CSSValueDefinition(value_type=10, index=1, resolved_value="var(--var-a)")],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

        builder = DependencyGraphBuilder()
        graph = builder._build_variable_dependencies_graph(vars_with_circular)

        # Should detect dependencies (but won't cause infinite loop)
        assert "--var-a" in graph["adjacency"]
        assert "--var-b" in graph["adjacency"]

    def test_class_without_dependencies(self):
        """Test class with no variable or asset dependencies."""
        classes = [
            CSSClass(
                name=".simple-class",
                stylesheet="Test",
                bundle="test.bundle",
                properties=[],
                variables_used=[],
                asset_dependencies=[],
                first_seen="2026.1.0",
                last_seen="2026.4.0",
            ),
        ]

        builder = DependencyGraphBuilder()
        graph = builder._build_class_to_variables_graph(classes)

        assert ".simple-class" in graph["adjacency"]
        assert len(graph["adjacency"][".simple-class"]) == 0
