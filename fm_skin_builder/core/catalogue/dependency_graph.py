"""
Dependency Graph Builder

Generates dependency graphs for CSS/USS assets:
- Variable → Classes (classes using each variable)
- Class → Variables (variables used by each class)
- Sprite → Classes (classes referencing each sprite/asset)
- Variable → Variables (variables referencing other variables)

Output format: Adjacency lists + node/edge metadata for visualization.
"""

from __future__ import annotations
from typing import Dict, List, Any, Set
from collections import defaultdict

from .models import CSSVariable, CSSClass
from ..logger import get_logger

log = get_logger(__name__)


class DependencyGraphBuilder:
    """Builds dependency graphs for CSS/USS assets."""

    def build_graphs(
        self,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
    ) -> Dict[str, Any]:
        """
        Build all dependency graphs.

        Args:
            css_variables: List of CSS variables
            css_classes: List of CSS classes

        Returns:
            Dictionary containing all graphs with nodes and edges
        """
        graphs = {
            "variable_to_classes": self._build_variable_to_classes_graph(
                css_variables, css_classes
            ),
            "class_to_variables": self._build_class_to_variables_graph(
                css_classes
            ),
            "sprite_to_classes": self._build_sprite_to_classes_graph(
                css_classes
            ),
            "variable_dependencies": self._build_variable_dependencies_graph(
                css_variables
            ),
        }

        return graphs

    def _build_variable_to_classes_graph(
        self,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
    ) -> Dict[str, Any]:
        """
        Build Variable → Classes graph.

        Args:
            css_variables: List of CSS variables
            css_classes: List of CSS classes

        Returns:
            Graph with adjacency list and metadata
        """
        # Build adjacency list
        adjacency: Dict[str, List[str]] = defaultdict(list)

        for css_class in css_classes:
            for var_name in css_class.variables_used:
                adjacency[var_name].append(css_class.name)

        # Build nodes metadata
        nodes = []
        for var in css_variables:
            nodes.append(
                {
                    "id": var.name,
                    "type": "variable",
                    "stylesheet": var.stylesheet,
                    "bundle": var.bundle,
                    "colors": var.colors,
                    "usage_count": len(adjacency.get(var.name, [])),
                }
            )

        # Build edges
        edges = []
        for var_name, class_names in adjacency.items():
            for class_name in class_names:
                edges.append(
                    {
                        "from": var_name,
                        "to": class_name,
                        "type": "uses_variable",
                    }
                )

        return {
            "adjacency": dict(adjacency),
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_variables": len(nodes),
                "total_edges": len(edges),
                "most_used_variables": self._get_top_n_by_usage(adjacency, 10),
            },
        }

    def _build_class_to_variables_graph(
        self,
        css_classes: List[CSSClass],
    ) -> Dict[str, Any]:
        """
        Build Class → Variables graph.

        Args:
            css_classes: List of CSS classes

        Returns:
            Graph with adjacency list and metadata
        """
        # Build adjacency list
        adjacency: Dict[str, List[str]] = {}

        for css_class in css_classes:
            adjacency[css_class.name] = css_class.variables_used

        # Build nodes metadata
        nodes = []
        for css_class in css_classes:
            nodes.append(
                {
                    "id": css_class.name,
                    "type": "class",
                    "stylesheet": css_class.stylesheet,
                    "bundle": css_class.bundle,
                    "variable_count": len(css_class.variables_used),
                    "asset_count": len(css_class.asset_dependencies),
                }
            )

        # Build edges
        edges = []
        for class_name, var_names in adjacency.items():
            for var_name in var_names:
                edges.append(
                    {
                        "from": class_name,
                        "to": var_name,
                        "type": "references_variable",
                    }
                )

        return {
            "adjacency": adjacency,
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_classes": len(nodes),
                "total_edges": len(edges),
                "classes_with_most_variables": self._get_top_n_by_usage(
                    adjacency, 10
                ),
            },
        }

    def _build_sprite_to_classes_graph(
        self,
        css_classes: List[CSSClass],
    ) -> Dict[str, Any]:
        """
        Build Sprite/Asset → Classes graph.

        Args:
            css_classes: List of CSS classes

        Returns:
            Graph with adjacency list and metadata
        """
        # Build adjacency list
        adjacency: Dict[str, List[str]] = defaultdict(list)

        for css_class in css_classes:
            for asset in css_class.asset_dependencies:
                adjacency[asset].append(css_class.name)

        # Build nodes metadata (for sprites/assets)
        nodes = []
        for asset_name in adjacency.keys():
            nodes.append(
                {
                    "id": asset_name,
                    "type": "asset",
                    "usage_count": len(adjacency[asset_name]),
                }
            )

        # Build edges
        edges = []
        for asset_name, class_names in adjacency.items():
            for class_name in class_names:
                edges.append(
                    {
                        "from": asset_name,
                        "to": class_name,
                        "type": "used_by_class",
                    }
                )

        return {
            "adjacency": dict(adjacency),
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_assets": len(nodes),
                "total_edges": len(edges),
                "most_used_assets": self._get_top_n_by_usage(adjacency, 10),
            },
        }

    def _build_variable_dependencies_graph(
        self,
        css_variables: List[CSSVariable],
    ) -> Dict[str, Any]:
        """
        Build Variable → Variable dependencies graph.

        Tracks variables that reference other variables (e.g., var(--other-var)).

        Args:
            css_variables: List of CSS variables

        Returns:
            Graph with adjacency list and metadata
        """
        import re

        var_ref_pattern = re.compile(r"var\((--[\w-]+)\)")

        # Build adjacency list
        adjacency: Dict[str, List[str]] = defaultdict(list)

        for var in css_variables:
            # Check if this variable's value references other variables
            # Find var() references in the value string
            matches = var_ref_pattern.findall(var.value)
            for ref_var in matches:
                if ref_var != var.name:  # Skip self-references
                    adjacency[var.name].append(ref_var)

        # Build nodes metadata
        nodes = []
        all_vars = set([v.name for v in css_variables])
        for var_name in all_vars:
            nodes.append(
                {
                    "id": var_name,
                    "type": "variable",
                    "depends_on_count": len(adjacency.get(var_name, [])),
                }
            )

        # Build edges
        edges = []
        for var_name, dep_vars in adjacency.items():
            for dep_var in dep_vars:
                edges.append(
                    {
                        "from": var_name,
                        "to": dep_var,
                        "type": "depends_on",
                    }
                )

        return {
            "adjacency": dict(adjacency),
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_variables": len(nodes),
                "total_dependencies": len(edges),
                "variables_with_dependencies": len(
                    [v for v in adjacency.values() if v]
                ),
            },
        }

    def _get_top_n_by_usage(
        self, adjacency: Dict[str, List[str]], n: int
    ) -> List[Dict[str, Any]]:
        """
        Get top N items by usage count.

        Args:
            adjacency: Adjacency list
            n: Number of top items to return

        Returns:
            List of {name, count} dictionaries
        """
        usage_counts = [
            {"name": name, "count": len(targets)}
            for name, targets in adjacency.items()
        ]

        # Sort by count descending
        usage_counts.sort(key=lambda x: x["count"], reverse=True)

        return usage_counts[:n]


def build_dependency_graphs(
    css_variables: List[CSSVariable],
    css_classes: List[CSSClass],
) -> Dict[str, Any]:
    """
    Convenience function to build all dependency graphs.

    Args:
        css_variables: List of CSS variables
        css_classes: List of CSS classes

    Returns:
        Dictionary containing all dependency graphs
    """
    builder = DependencyGraphBuilder()
    return builder.build_graphs(css_variables, css_classes)
