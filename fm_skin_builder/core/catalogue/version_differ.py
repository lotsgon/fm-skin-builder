"""
Version Differ

Compares two catalogue versions and generates detailed changelogs
tracking additions, removals, and modifications across all asset types.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from ..logger import get_logger

log = get_logger(__name__)


class AssetChange:
    """Represents a change to a single asset."""

    def __init__(
        self,
        asset_type: str,
        name: str,
        change_type: str,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize asset change.

        Args:
            asset_type: Type of asset (css_variable, css_class, sprite, texture, font)
            name: Asset name
            change_type: added, removed, or modified
            old_data: Previous asset data (for removed/modified)
            new_data: New asset data (for added/modified)
            details: Additional change details (what changed)
        """
        self.asset_type = asset_type
        self.name = name
        self.change_type = change_type
        self.old_data = old_data or {}
        self.new_data = new_data or {}
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        result = {
            "asset_type": self.asset_type,
            "name": self.name,
            "change_type": self.change_type,
        }

        if self.details:
            result["details"] = self.details

        return result


class VersionDiffer:
    """Compares two catalogue versions and generates changelogs."""

    def __init__(self, old_version_dir: Path, new_version_dir: Path):
        """
        Initialize version differ.

        Args:
            old_version_dir: Directory containing old catalogue version
            new_version_dir: Directory containing new catalogue version
        """
        self.old_version_dir = old_version_dir
        self.new_version_dir = new_version_dir

        # Loaded data
        self.old_metadata: Dict[str, Any] = {}
        self.new_metadata: Dict[str, Any] = {}
        self.old_css_variables: List[Dict[str, Any]] = []
        self.new_css_variables: List[Dict[str, Any]] = []
        self.old_css_classes: List[Dict[str, Any]] = []
        self.new_css_classes: List[Dict[str, Any]] = []
        self.old_sprites: List[Dict[str, Any]] = []
        self.new_sprites: List[Dict[str, Any]] = []
        self.old_textures: List[Dict[str, Any]] = []
        self.new_textures: List[Dict[str, Any]] = []
        self.old_fonts: List[Dict[str, Any]] = []
        self.new_fonts: List[Dict[str, Any]] = []

        # Changes
        self.changes: List[AssetChange] = []

    def load_catalogues(self) -> None:
        """Load both catalogue versions from disk."""
        log.info(f"Loading old catalogue from {self.old_version_dir}")
        self.old_metadata = self._load_json(self.old_version_dir / "metadata.json")
        self._check_schema_version(self.old_metadata, "old")

        self.old_css_variables = self._load_json(
            self.old_version_dir / "css-variables.json"
        )
        self.old_css_classes = self._load_json(
            self.old_version_dir / "css-classes.json"
        )
        self.old_sprites = self._load_json(self.old_version_dir / "sprites.json")
        self.old_textures = self._load_json(self.old_version_dir / "textures.json")
        self.old_fonts = self._load_json(self.old_version_dir / "fonts.json")

        log.info(f"Loading new catalogue from {self.new_version_dir}")
        self.new_metadata = self._load_json(self.new_version_dir / "metadata.json")
        self._check_schema_version(self.new_metadata, "new")

        self.new_css_variables = self._load_json(
            self.new_version_dir / "css-variables.json"
        )
        self.new_css_classes = self._load_json(
            self.new_version_dir / "css-classes.json"
        )
        self.new_sprites = self._load_json(self.new_version_dir / "sprites.json")
        self.new_textures = self._load_json(self.new_version_dir / "textures.json")
        self.new_fonts = self._load_json(self.new_version_dir / "fonts.json")

    def _check_schema_version(self, metadata: Dict[str, Any], label: str) -> None:
        """
        Check schema version and warn about compatibility.

        Args:
            metadata: Metadata dictionary
            label: Label for logging (old/new)
        """
        schema_version = metadata.get("schema_version", "1.0.0")

        if schema_version == "1.0.0":
            log.warning(
                f"  {label.capitalize()} catalogue uses old schema v1.0.0 (pre-change tracking)"
            )
            log.warning("  Some comparison features may be limited")
        elif schema_version.startswith("2.0"):
            log.info(f"  {label.capitalize()} catalogue schema: {schema_version}")
        elif schema_version.startswith("2.1"):
            log.info(
                f"  {label.capitalize()} catalogue schema: {schema_version} (with change tracking)"
            )
        else:
            log.warning(
                f"  {label.capitalize()} catalogue has unknown schema: {schema_version}"
            )

    def _load_json(self, path: Path) -> Any:
        """Load JSON file."""
        if not path.exists():
            log.warning(f"File not found: {path}")
            return [] if path.suffix == ".json" and "metadata" not in path.name else {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _colors_are_similar(
        self, old_colors: List[str], new_colors: List[str], tolerance: int = 2
    ) -> bool:
        """
        Check if two color lists are similar within a tolerance.

        This filters out false positives from minor color variations due to:
        - Image processing/quantization artifacts
        - Different color palette extraction runs
        - Floating point rounding errors

        Args:
            old_colors: List of hex colors from old version
            new_colors: List of hex colors from new version
            tolerance: Maximum RGB value difference to consider colors identical (default: 2)

        Returns:
            True if all colors are within tolerance, False otherwise
        """
        # Different number of colors = definitely different
        if len(old_colors) != len(new_colors):
            return False

        # Empty lists are considered similar
        if len(old_colors) == 0:
            return True

        # Compare each color pair
        for old_hex, new_hex in zip(old_colors, new_colors):
            # Parse hex to RGB
            try:
                old_hex = old_hex.lstrip("#")
                new_hex = new_hex.lstrip("#")

                old_r = int(old_hex[0:2], 16)
                old_g = int(old_hex[2:4], 16)
                old_b = int(old_hex[4:6], 16)

                new_r = int(new_hex[0:2], 16)
                new_g = int(new_hex[2:4], 16)
                new_b = int(new_hex[4:6], 16)

                # Check if any channel differs by more than tolerance
                if (
                    abs(old_r - new_r) > tolerance
                    or abs(old_g - new_g) > tolerance
                    or abs(old_b - new_b) > tolerance
                ):
                    return False

            except (ValueError, IndexError):
                # Invalid hex format - consider different
                return False

        # All colors within tolerance
        return True

    def _is_asset_ref_only_change(self, old_val: str, new_val: str) -> bool:
        """
        Check if a property change is only due to unstable asset reference indices
        or format migration from placeholder to resolved format.

        Unity USS stores asset references as <asset-ref:INDEX> where INDEX can change
        between builds even if the actual asset stays the same.

        Additionally, when old catalogues were built before asset resolution was
        implemented, they have placeholders while new catalogues have resolved names.
        This detects and filters out such format migration changes.

        Args:
            old_val: Old property value
            new_val: New property value

        Returns:
            True if this is a false positive (both placeholders OR mixed placeholder/resolved)
        """
        import re

        # Pattern to match <asset-ref:NNN> where NNN is a number
        asset_ref_pattern = r'^<asset-ref:\d+>$'
        # Pattern to match resource("AssetName")
        resource_pattern = r'^resource\(["\']([^"\']+)["\']\)$'

        # Check if both are asset-ref placeholders
        old_is_placeholder = bool(re.match(asset_ref_pattern, old_val.strip()))
        new_is_placeholder = bool(re.match(asset_ref_pattern, new_val.strip()))

        # Check if either is a resolved resource() reference
        old_is_resolved = bool(re.match(resource_pattern, old_val.strip()))
        new_is_resolved = bool(re.match(resource_pattern, new_val.strip()))

        # Case 1: Both are placeholders with different indices - false positive
        if old_is_placeholder and new_is_placeholder:
            return True

        # Case 2: Mixed format (old=placeholder, new=resolved) - format migration
        # This happens when comparing catalogues built before/after asset resolution was implemented
        if old_is_placeholder and new_is_resolved:
            log.info(
                f"Skipping format migration: {old_val} -> {new_val} "
                "(old catalogue built before asset resolution)"
            )
            return True

        # Case 3: Mixed format reversed (old=resolved, new=placeholder) - shouldn't happen but handle it
        if old_is_resolved and new_is_placeholder:
            log.warning(
                f"Unexpected format regression: {old_val} -> {new_val} "
                "(new catalogue has placeholder but old had resolved name)"
            )
            return True

        # Not a false positive - this is a real change
        return False

    def compare(self) -> Dict[str, Any]:
        """
        Compare catalogues and generate changelog.

        Returns:
            Detailed changelog dictionary
        """
        log.info("Comparing catalogues...")

        # Compare each asset type
        self._compare_css_variables()
        self._compare_css_classes()
        self._compare_sprites()
        self._compare_textures()
        self._compare_fonts()

        # Generate changelog
        changelog = self._generate_changelog()

        log.info("Comparison complete")
        log.info(f"  Total changes: {len(self.changes)}")

        return changelog

    def _compare_css_variables(self) -> None:
        """Compare CSS variables between versions."""
        log.info("  Comparing CSS variables...")

        old_vars = {v["name"]: v for v in self.old_css_variables}
        new_vars = {v["name"]: v for v in self.new_css_variables}

        old_names = set(old_vars.keys())
        new_names = set(new_vars.keys())

        # Added variables
        added = new_names - old_names
        for name in added:
            var = new_vars[name]
            details = {
                "stylesheet": var.get("stylesheet"),
                "property_name": var.get("property_name"),
                "values": self._format_css_values(var.get("values", [])),
                "colors": var.get("colors", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="css_variable",
                    name=name,
                    change_type="added",
                    new_data=var,
                    details=details,
                )
            )

        # Removed variables
        removed = old_names - new_names
        for name in removed:
            var = old_vars[name]
            details = {
                "stylesheet": var.get("stylesheet"),
                "property_name": var.get("property_name"),
                "values": self._format_css_values(var.get("values", [])),
            }
            self.changes.append(
                AssetChange(
                    asset_type="css_variable",
                    name=name,
                    change_type="removed",
                    old_data=var,
                    details=details,
                )
            )

        # Modified variables
        common = old_names & new_names
        for name in common:
            old_var = old_vars[name]
            new_var = new_vars[name]

            # Compare values
            old_values = self._format_css_values(old_var.get("values", []))
            new_values = self._format_css_values(new_var.get("values", []))

            if old_values != new_values:
                details = {
                    "stylesheet": new_var.get("stylesheet"),
                    "property_name": new_var.get("property_name"),
                    "old_values": old_values,
                    "new_values": new_values,
                    "old_colors": old_var.get("colors", []),
                    "new_colors": new_var.get("colors", []),
                }
                self.changes.append(
                    AssetChange(
                        asset_type="css_variable",
                        name=name,
                        change_type="modified",
                        old_data=old_var,
                        new_data=new_var,
                        details=details,
                    )
                )

        log.info(
            f"    Added: {len(added)}, Removed: {len(removed)}, Modified: {len([c for c in self.changes if c.asset_type == 'css_variable' and c.change_type == 'modified'])}"
        )

    def _compare_css_classes(self) -> None:
        """Compare CSS classes between versions."""
        log.info("  Comparing CSS classes...")

        old_classes = {c["name"]: c for c in self.old_css_classes}
        new_classes = {c["name"]: c for c in self.new_css_classes}

        old_names = set(old_classes.keys())
        new_names = set(new_classes.keys())

        # Added classes
        added = new_names - old_names
        for name in added:
            cls = new_classes[name]
            details = {
                "stylesheet": cls.get("stylesheet"),
                "properties": self._format_css_properties(cls.get("properties", [])),
                "variables_used": cls.get("variables_used", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="css_class",
                    name=name,
                    change_type="added",
                    new_data=cls,
                    details=details,
                )
            )

        # Removed classes
        removed = old_names - new_names
        for name in removed:
            cls = old_classes[name]
            details = {
                "stylesheet": cls.get("stylesheet"),
                "properties": self._format_css_properties(cls.get("properties", [])),
            }
            self.changes.append(
                AssetChange(
                    asset_type="css_class",
                    name=name,
                    change_type="removed",
                    old_data=cls,
                    details=details,
                )
            )

        # Modified classes
        common = old_names & new_names
        for name in common:
            old_cls = old_classes[name]
            new_cls = new_classes[name]

            # Detailed property-level comparison
            property_diff = self._compare_class_properties(old_cls, new_cls)

            if property_diff["has_changes"]:
                details = {
                    "stylesheet": new_cls.get("stylesheet"),
                    "added_properties": property_diff["added"],
                    "removed_properties": property_diff["removed"],
                    "modified_properties": property_diff["modified"],
                    "old_variables_used": old_cls.get("variables_used", []),
                    "new_variables_used": new_cls.get("variables_used", []),
                    "variable_changes": property_diff["variable_changes"],
                    "asset_changes": property_diff["asset_changes"],
                }
                self.changes.append(
                    AssetChange(
                        asset_type="css_class",
                        name=name,
                        change_type="modified",
                        old_data=old_cls,
                        new_data=new_cls,
                        details=details,
                    )
                )

        log.info(
            f"    Added: {len(added)}, Removed: {len(removed)}, Modified: {len([c for c in self.changes if c.asset_type == 'css_class' and c.change_type == 'modified'])}"
        )

    def _compare_sprites(self) -> None:
        """Compare sprites between versions."""
        log.info("  Comparing sprites...")

        old_sprites = {s["name"]: s for s in self.old_sprites}
        new_sprites = {s["name"]: s for s in self.new_sprites}

        old_names = set(old_sprites.keys())
        new_names = set(new_sprites.keys())

        # Added sprites
        added = new_names - old_names
        for name in added:
            sprite = new_sprites[name]
            details = {
                "width": sprite.get("width"),
                "height": sprite.get("height"),
                "has_vertex_data": sprite.get("has_vertex_data"),
                "dominant_colors": sprite.get("dominant_colors", []),
                "tags": sprite.get("tags", []),
                "bundles": sprite.get("bundles", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="sprite",
                    name=name,
                    change_type="added",
                    new_data=sprite,
                    details=details,
                )
            )

        # Removed sprites
        removed = old_names - new_names
        for name in removed:
            sprite = old_sprites[name]
            details = {
                "width": sprite.get("width"),
                "height": sprite.get("height"),
                "bundles": sprite.get("bundles", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="sprite",
                    name=name,
                    change_type="removed",
                    old_data=sprite,
                    details=details,
                )
            )

        # Modified sprites (check content_hash)
        common = old_names & new_names
        for name in common:
            old_sprite = old_sprites[name]
            new_sprite = new_sprites[name]

            old_hash = old_sprite.get("content_hash", "")
            new_hash = new_sprite.get("content_hash", "")

            if old_hash and new_hash and old_hash != new_hash:
                # Content hash changed - but check if it's just minor color variations
                old_colors = old_sprite.get("dominant_colors", [])
                new_colors = new_sprite.get("dominant_colors", [])

                # If dimensions are the same AND colors are very similar (within tolerance),
                # this is likely just quantization/extraction artifacts - skip it
                old_dims = (old_sprite.get("width"), old_sprite.get("height"))
                new_dims = (new_sprite.get("width"), new_sprite.get("height"))

                if old_dims == new_dims and self._colors_are_similar(
                    old_colors, new_colors, tolerance=2
                ):
                    # Colors are within tolerance - skip this as a false positive
                    log.debug(
                        f"Skipping sprite {name} - colors within tolerance "
                        f"(hash changed but likely due to minor quantization artifacts)"
                    )
                    continue

                # Significant change - report it
                details = {
                    "old_dimensions": f"{old_sprite.get('width')}x{old_sprite.get('height')}",
                    "new_dimensions": f"{new_sprite.get('width')}x{new_sprite.get('height')}",
                    "old_colors": old_colors,
                    "new_colors": new_colors,
                    "content_changed": True,
                }
                self.changes.append(
                    AssetChange(
                        asset_type="sprite",
                        name=name,
                        change_type="modified",
                        old_data=old_sprite,
                        new_data=new_sprite,
                        details=details,
                    )
                )

        log.info(
            f"    Added: {len(added)}, Removed: {len(removed)}, Modified: {len([c for c in self.changes if c.asset_type == 'sprite' and c.change_type == 'modified'])}"
        )

    def _compare_textures(self) -> None:
        """Compare textures between versions."""
        log.info("  Comparing textures...")

        old_textures = {t["name"]: t for t in self.old_textures}
        new_textures = {t["name"]: t for t in self.new_textures}

        old_names = set(old_textures.keys())
        new_names = set(new_textures.keys())

        # Added textures
        added = new_names - old_names
        for name in added:
            texture = new_textures[name]
            details = {
                "width": texture.get("width"),
                "height": texture.get("height"),
                "type": texture.get("type"),
                "dominant_colors": texture.get("dominant_colors", []),
                "tags": texture.get("tags", []),
                "bundles": texture.get("bundles", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="texture",
                    name=name,
                    change_type="added",
                    new_data=texture,
                    details=details,
                )
            )

        # Removed textures
        removed = old_names - new_names
        for name in removed:
            texture = old_textures[name]
            details = {
                "width": texture.get("width"),
                "height": texture.get("height"),
                "type": texture.get("type"),
                "bundles": texture.get("bundles", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="texture",
                    name=name,
                    change_type="removed",
                    old_data=texture,
                    details=details,
                )
            )

        # Modified textures (check content_hash)
        common = old_names & new_names
        for name in common:
            old_texture = old_textures[name]
            new_texture = new_textures[name]

            old_hash = old_texture.get("content_hash", "")
            new_hash = new_texture.get("content_hash", "")

            if old_hash and new_hash and old_hash != new_hash:
                # Content hash changed - but check if it's just minor color variations
                old_colors = old_texture.get("dominant_colors", [])
                new_colors = new_texture.get("dominant_colors", [])

                # If dimensions are the same AND colors are very similar (within tolerance),
                # this is likely just quantization/extraction artifacts - skip it
                old_dims = (old_texture.get("width"), old_texture.get("height"))
                new_dims = (new_texture.get("width"), new_texture.get("height"))

                if old_dims == new_dims and self._colors_are_similar(
                    old_colors, new_colors, tolerance=2
                ):
                    # Colors are within tolerance - skip this as a false positive
                    log.debug(
                        f"Skipping texture {name} - colors within tolerance "
                        f"(hash changed but likely due to minor quantization artifacts)"
                    )
                    continue

                # Significant change - report it
                details = {
                    "old_dimensions": f"{old_texture.get('width')}x{old_texture.get('height')}",
                    "new_dimensions": f"{new_texture.get('width')}x{new_texture.get('height')}",
                    "old_colors": old_colors,
                    "new_colors": new_colors,
                    "content_changed": True,
                }
                self.changes.append(
                    AssetChange(
                        asset_type="texture",
                        name=name,
                        change_type="modified",
                        old_data=old_texture,
                        new_data=new_texture,
                        details=details,
                    )
                )

        log.info(
            f"    Added: {len(added)}, Removed: {len(removed)}, Modified: {len([c for c in self.changes if c.asset_type == 'texture' and c.change_type == 'modified'])}"
        )

    def _compare_fonts(self) -> None:
        """Compare fonts between versions."""
        log.info("  Comparing fonts...")

        old_fonts = {f["name"]: f for f in self.old_fonts}
        new_fonts = {f["name"]: f for f in self.new_fonts}

        old_names = set(old_fonts.keys())
        new_names = set(new_fonts.keys())

        # Added fonts
        added = new_names - old_names
        for name in added:
            font = new_fonts[name]
            details = {
                "bundles": font.get("bundles", []),
                "tags": font.get("tags", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="font",
                    name=name,
                    change_type="added",
                    new_data=font,
                    details=details,
                )
            )

        # Removed fonts
        removed = old_names - new_names
        for name in removed:
            font = old_fonts[name]
            details = {
                "bundles": font.get("bundles", []),
            }
            self.changes.append(
                AssetChange(
                    asset_type="font",
                    name=name,
                    change_type="removed",
                    old_data=font,
                    details=details,
                )
            )

        # Fonts don't typically get "modified" - they're either added or removed

        log.info(f"    Added: {len(added)}, Removed: {len(removed)}")

    def _format_css_values(self, values: List[Dict[str, Any]]) -> str:
        """Format CSS values for comparison."""
        if not values:
            return ""
        return ", ".join(v.get("resolved_value", "") for v in values)

    def _format_css_properties(self, properties: List[Dict[str, Any]]) -> str:
        """Format CSS properties for comparison."""
        if not properties:
            return ""
        result = []
        for prop in properties:
            name = prop.get("name", "")
            values = self._format_css_values(prop.get("values", []))
            result.append(f"{name}: {values}")
        return "; ".join(result)

    def _generate_changelog(self) -> Dict[str, Any]:
        """Generate comprehensive changelog from detected changes."""
        # Group changes by asset type and change type
        changelog = {
            "from_version": self.old_metadata.get("fm_version", "unknown"),
            "to_version": self.new_metadata.get("fm_version", "unknown"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {},
            "changes_by_type": {},
            "changes_by_stylesheet": {},
        }

        # Build summary
        for asset_type in [
            "css_variable",
            "css_class",
            "sprite",
            "texture",
            "font",
        ]:
            changes = [c for c in self.changes if c.asset_type == asset_type]
            added = len([c for c in changes if c.change_type == "added"])
            removed = len([c for c in changes if c.change_type == "removed"])
            modified = len([c for c in changes if c.change_type == "modified"])

            changelog["summary"][asset_type] = {
                "added": added,
                "removed": removed,
                "modified": modified,
                "total": added + removed + modified,
            }

        # Build detailed changes by type
        for asset_type in [
            "css_variable",
            "css_class",
            "sprite",
            "texture",
            "font",
        ]:
            changes = [c for c in self.changes if c.asset_type == asset_type]

            changelog["changes_by_type"][asset_type] = {
                "added": [c.to_dict() for c in changes if c.change_type == "added"],
                "removed": [c.to_dict() for c in changes if c.change_type == "removed"],
                "modified": [
                    c.to_dict() for c in changes if c.change_type == "modified"
                ],
            }

        # Build per-stylesheet breakdown for CSS changes
        css_changes = [
            c for c in self.changes if c.asset_type in ["css_variable", "css_class"]
        ]

        stylesheet_breakdown = {}
        for change in css_changes:
            stylesheet = change.details.get("stylesheet", "unknown")
            if stylesheet not in stylesheet_breakdown:
                stylesheet_breakdown[stylesheet] = {
                    "css_variables": {"added": [], "removed": [], "modified": []},
                    "css_classes": {"added": [], "removed": [], "modified": []},
                }

            asset_key = (
                "css_variables"
                if change.asset_type == "css_variable"
                else "css_classes"
            )
            stylesheet_breakdown[stylesheet][asset_key][change.change_type].append(
                change.to_dict()
            )

        changelog["changes_by_stylesheet"] = stylesheet_breakdown

        return changelog

    def generate_html_report(self, changelog: Dict[str, Any]) -> str:
        """
        Generate HTML report from changelog.

        Args:
            changelog: Changelog dictionary

        Returns:
            HTML string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>FM Asset Catalogue Changelog</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            text-transform: uppercase;
            color: #666;
        }}
        .stat {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
        }}
        .stat .label {{
            color: #666;
        }}
        .added {{ color: #22c55e; font-weight: bold; }}
        .removed {{ color: #ef4444; font-weight: bold; }}
        .modified {{ color: #f59e0b; font-weight: bold; }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .change-item {{
            border-left: 3px solid #e5e7eb;
            padding: 10px 15px;
            margin: 10px 0;
            background: #f9fafb;
        }}
        .change-item.added {{ border-left-color: #22c55e; }}
        .change-item.removed {{ border-left-color: #ef4444; }}
        .change-item.modified {{ border-left-color: #f59e0b; }}
        .change-name {{
            font-weight: bold;
            font-family: 'Courier New', monospace;
            color: #111827;
        }}
        .change-details {{
            margin-top: 5px;
            font-size: 14px;
            color: #6b7280;
        }}
        .color-swatch {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 1px solid #ddd;
            margin: 0 2px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FM Asset Catalogue Changelog</h1>
        <p><strong>From:</strong> {changelog['from_version']} → <strong>To:</strong> {changelog['to_version']}</p>
        <p><strong>Generated:</strong> {changelog['generated_at']}</p>
    </div>

    <div class="summary">
"""

        # Add summary cards
        for asset_type, stats in changelog["summary"].items():
            display_name = asset_type.replace("_", " ").title()
            html += f"""
        <div class="summary-card">
            <h3>{display_name}</h3>
            <div class="stat">
                <span class="label">Added:</span>
                <span class="added">{stats['added']}</span>
            </div>
            <div class="stat">
                <span class="label">Removed:</span>
                <span class="removed">{stats['removed']}</span>
            </div>
            <div class="stat">
                <span class="label">Modified:</span>
                <span class="modified">{stats['modified']}</span>
            </div>
            <div class="stat">
                <span class="label">Total:</span>
                <span>{stats['total']}</span>
            </div>
        </div>
"""

        html += """
    </div>
"""

        # Add per-stylesheet breakdown
        if changelog.get("changes_by_stylesheet"):
            html += """
    <div class="section">
        <h2>Changes by Stylesheet</h2>
"""
            for stylesheet, changes in changelog["changes_by_stylesheet"].items():
                html += f"""
        <h3>{stylesheet}</h3>
"""
                # CSS Variables
                if any(changes["css_variables"].values()):
                    html += "<h4>CSS Variables</h4>"
                    for change in changes["css_variables"]["added"]:
                        html += self._format_change_html(change, "added")
                    for change in changes["css_variables"]["removed"]:
                        html += self._format_change_html(change, "removed")
                    for change in changes["css_variables"]["modified"]:
                        html += self._format_change_html(change, "modified")

                # CSS Classes
                if any(changes["css_classes"].values()):
                    html += "<h4>CSS Classes</h4>"
                    for change in changes["css_classes"]["added"]:
                        html += self._format_change_html(change, "added")
                    for change in changes["css_classes"]["removed"]:
                        html += self._format_change_html(change, "removed")
                    for change in changes["css_classes"]["modified"]:
                        html += self._format_change_html(change, "modified")

            html += """
    </div>
"""

        # Add other asset types
        for asset_type in ["sprite", "texture", "font"]:
            type_changes = changelog["changes_by_type"].get(asset_type, {})
            if any(type_changes.values()):
                display_name = asset_type.replace("_", " ").title() + "s"
                html += f"""
    <div class="section">
        <h2>{display_name}</h2>
"""
                for change in type_changes.get("added", []):
                    html += self._format_change_html(change, "added")
                for change in type_changes.get("removed", []):
                    html += self._format_change_html(change, "removed")
                for change in type_changes.get("modified", []):
                    html += self._format_change_html(change, "modified")

                html += """
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def _format_change_html(self, change: Dict[str, Any], change_type: str) -> str:
        """Format a single change as HTML."""
        name = change["name"]
        details = change.get("details", {})

        html = f'<div class="change-item {change_type}">'
        html += f'<div class="change-name">{name}</div>'
        html += '<div class="change-details">'

        if change_type == "added":
            if "values" in details:
                html += f"<div>Value: {details['values']}</div>"
            if "colors" in details and details["colors"]:
                html += "<div>Colors: "
                for color in details["colors"]:
                    html += f'<span class="color-swatch" style="background: {color}"></span> {color} '
                html += "</div>"
            if "dimensions" in details or "width" in details:
                width = details.get("width", "")
                height = details.get("height", "")
                html += f"<div>Dimensions: {width}x{height}</div>"

        elif change_type == "removed":
            if "values" in details:
                html += f"<div>Previous value: {details['values']}</div>"

        elif change_type == "modified":
            if "old_values" in details and "new_values" in details:
                html += f"<div>Old: {details['old_values']}</div>"
                html += f"<div>New: {details['new_values']}</div>"
            if "old_dimensions" in details and "new_dimensions" in details:
                html += f"<div>Old: {details['old_dimensions']}</div>"
                html += f"<div>New: {details['new_dimensions']}</div>"

        html += "</div></div>"
        return html

    def _compare_class_properties(
        self, old_cls: Dict[str, Any], new_cls: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare CSS class properties at a detailed level.

        Detects:
        - Added properties
        - Removed properties
        - Modified property values (both raw and resolved)
        - Variable reference changes
        - Asset dependency changes

        Args:
            old_cls: Old class data
            new_cls: New class data

        Returns:
            Dictionary with detailed property changes
        """
        # Get raw and resolved properties
        # Note: Use .get() without default to get None if key doesn't exist
        old_raw = old_cls.get("raw_properties")
        new_raw = new_cls.get("raw_properties")

        # Note: resolved_properties was removed in schema simplification
        # We now only compare raw_properties
        old_resolved = old_cls.get("resolved_properties") or {}
        new_resolved = new_cls.get("resolved_properties") or {}

        # If enhanced properties not available, fall back to basic comparison
        if old_raw is None and new_raw is None:
            old_props = self._format_css_properties(old_cls.get("properties", []))
            new_props = self._format_css_properties(new_cls.get("properties", []))
            return {
                "has_changes": old_props != new_props,
                "added": [],
                "removed": [],
                "modified": [],
                "variable_changes": [],
                "asset_changes": [],
            }

        old_prop_names = set(old_raw.keys()) if old_raw else set()
        new_prop_names = set(new_raw.keys()) if new_raw else set()

        # Detect added/removed properties
        added = new_prop_names - old_prop_names
        removed = old_prop_names - new_prop_names
        common = old_prop_names & new_prop_names

        # Detect modified properties
        modified = []
        for prop_name in common:
            old_val = old_raw.get(prop_name, "")
            new_val = new_raw.get(prop_name, "")
            old_resolved_val = old_resolved.get(prop_name, "") if old_resolved else ""
            new_resolved_val = new_resolved.get(prop_name, "") if new_resolved else ""

            # Only compare raw values if resolved properties are not available
            # (they were removed in model simplification)
            if old_resolved or new_resolved:
                # Old catalogues might have resolved_properties
                has_changes = old_val != new_val or old_resolved_val != new_resolved_val
            else:
                # New catalogues only have raw_properties
                has_changes = old_val != new_val

                # IMPORTANT: Filter out false positives from unstable asset reference indices
                # Unity USS stores asset references as <asset-ref:INDEX> where INDEX can change
                # between builds even if the actual asset stays the same. We can't resolve these
                # to actual asset names without the Unity bundle, so we skip them entirely.
                # TODO: Implement proper asset reference resolution during extraction
                if has_changes and self._is_asset_ref_only_change(old_val, new_val):
                    # Both are asset-ref placeholders with different indices
                    # This is likely a false positive - skip it
                    has_changes = False
                    log.debug(
                        f"Skipping asset-ref index change in {prop_name}: {old_val} -> {new_val}"
                    )

            if has_changes:
                modified.append(
                    {
                        "property": prop_name,
                        "old_raw": old_val,
                        "new_raw": new_val,
                        "old_resolved": old_resolved_val,
                        "new_resolved": new_resolved_val,
                    }
                )

        # Detect variable reference changes
        old_vars = set(old_cls.get("variables_used", []))
        new_vars = set(new_cls.get("variables_used", []))
        var_changes = {
            "added": sorted(list(new_vars - old_vars)),
            "removed": sorted(list(old_vars - new_vars)),
        }

        # Detect asset dependency changes
        old_assets = set(old_cls.get("asset_dependencies", []))
        new_assets = set(new_cls.get("asset_dependencies", []))
        asset_changes = {
            "added": sorted(list(new_assets - old_assets)),
            "removed": sorted(list(old_assets - new_assets)),
        }

        has_changes = (
            len(added) > 0
            or len(removed) > 0
            or len(modified) > 0
            or len(var_changes["added"]) > 0
            or len(var_changes["removed"]) > 0
            or len(asset_changes["added"]) > 0
            or len(asset_changes["removed"]) > 0
        )

        return {
            "has_changes": has_changes,
            "added": [{"property": p, "value": new_raw.get(p, "")} for p in sorted(added)],
            "removed": [{"property": p, "value": old_raw.get(p, "")} for p in sorted(removed)],
            "modified": modified,
            "variable_changes": var_changes,
            "asset_changes": asset_changes,
        }
