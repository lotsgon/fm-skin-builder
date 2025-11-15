"""
Test enhanced version differ functionality (property-level diffing).
"""

import pytest
from fm_skin_builder.core.catalogue.version_differ import VersionDiffer


class TestVersionDifferEnhanced:
    """Test enhanced property-level CSS class diffing."""

    def test_compare_class_properties_basic(self):
        """Test basic property comparison."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
                "border-radius": "2px",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
                "border-radius": "2px",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert len(result["modified"]) == 1
        assert result["modified"][0]["property"] == "border-radius"
        assert result["modified"][0]["old_raw"] == "2px"
        assert result["modified"][0]["new_raw"] == "4px"

    def test_compare_class_properties_added(self):
        """Test detecting added properties."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert len(result["added"]) == 1
        assert result["added"][0]["property"] == "border-radius"
        assert result["added"][0]["value"] == "4px"

    def test_compare_class_properties_removed(self):
        """Test detecting removed properties."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
                "border-radius": "4px",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert len(result["removed"]) == 1
        assert result["removed"][0]["property"] == "border-radius"
        assert result["removed"][0]["value"] == "4px"

    def test_compare_variable_changes(self):
        """Test detecting variable reference changes."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": ["--primary", "--old-var"],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": ["--primary", "--new-var"],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert "--new-var" in result["variable_changes"]["added"]
        assert "--old-var" in result["variable_changes"]["removed"]

    def test_compare_asset_changes(self):
        """Test detecting asset dependency changes."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": [],
            "asset_dependencies": ["old/icon"],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": [],
            "asset_dependencies": ["old/icon", "new/icon"],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert "new/icon" in result["asset_changes"]["added"]
        assert len(result["asset_changes"]["removed"]) == 0

    def test_compare_variable_value_resolution_change(self):
        """Test detecting changes in resolved variable values."""
        differ = VersionDiffer(None, None)

        # Same raw value, but different resolved value (variable changed)
        old_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "var(--primary)",
            },
            "resolved_properties": {
                "color": "#2196F3",
            },
            "variables_used": ["--primary"],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "var(--primary)",
            },
            "resolved_properties": {
                "color": "#1976D2",
            },
            "variables_used": ["--primary"],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert len(result["modified"]) == 1
        assert result["modified"][0]["property"] == "color"
        assert result["modified"][0]["old_resolved"] == "#2196F3"
        assert result["modified"][0]["new_resolved"] == "#1976D2"

    def test_no_changes(self):
        """Test detecting no changes."""
        differ = VersionDiffer(None, None)

        cls_data = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
            },
            "variables_used": [],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(cls_data, cls_data)

        assert result["has_changes"] is False
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["modified"]) == 0

    def test_fallback_to_basic_comparison(self):
        """Test fallback when enhanced properties not available."""
        differ = VersionDiffer(None, None)

        # Classes without enhanced data
        old_cls = {
            "name": ".test-class",
            "properties": [
                {
                    "name": "color",
                    "values": [{"resolved_value": "#FFFFFF"}],
                }
            ],
        }

        new_cls = {
            "name": ".test-class",
            "properties": [
                {
                    "name": "color",
                    "values": [{"resolved_value": "#000000"}],
                }
            ],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        # Should still detect changes using fallback
        assert result["has_changes"] is True

    def test_multiple_property_changes(self):
        """Test detecting multiple simultaneous changes."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#FFFFFF",
                "border-radius": "2px",
            },
            "resolved_properties": {
                "color": "#FFFFFF",
                "border-radius": "2px",
            },
            "variables_used": ["--old-var"],
            "asset_dependencies": ["old/icon"],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {
                "color": "#000000",
                "border-radius": "4px",
                "padding": "10px",
            },
            "resolved_properties": {
                "color": "#000000",
                "border-radius": "4px",
                "padding": "10px",
            },
            "variables_used": ["--new-var"],
            "asset_dependencies": ["new/icon"],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is True
        assert len(result["added"]) == 1  # padding
        assert len(result["modified"]) == 2  # color, border-radius
        assert "--new-var" in result["variable_changes"]["added"]
        assert "--old-var" in result["variable_changes"]["removed"]
        assert "new/icon" in result["asset_changes"]["added"]
        assert "old/icon" in result["asset_changes"]["removed"]

    def test_empty_properties(self):
        """Test handling empty properties."""
        differ = VersionDiffer(None, None)

        old_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": [],
            "asset_dependencies": [],
        }

        new_cls = {
            "name": ".test-class",
            "raw_properties": {},
            "resolved_properties": {},
            "variables_used": [],
            "asset_dependencies": [],
        }

        result = differ._compare_class_properties(old_cls, new_cls)

        assert result["has_changes"] is False
