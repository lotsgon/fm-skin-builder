"""
Test bundle exclusion mechanism.
"""

import pytest
from pathlib import Path
from fm_skin_builder.core.catalogue.builder import CatalogueBuilder


class TestBundleExclusion:
    """Test bundle exclusion patterns."""

    @pytest.fixture
    def builder_with_exclusions(self, tmp_path):
        """Create builder with exclusion patterns."""
        icon_path = tmp_path / "icon.svg"
        icon_path.touch()

        return CatalogueBuilder(
            fm_version="2026.4.0",
            output_dir=tmp_path / "output",
            icon_white_path=icon_path,
            icon_black_path=icon_path,
            exclude_patterns=["newgen", "regen"],
        )

    @pytest.fixture
    def builder_without_exclusions(self, tmp_path):
        """Create builder without exclusion patterns."""
        icon_path = tmp_path / "icon.svg"
        icon_path.touch()

        return CatalogueBuilder(
            fm_version="2026.4.0",
            output_dir=tmp_path / "output",
            icon_white_path=icon_path,
            icon_black_path=icon_path,
        )

    @pytest.fixture
    def mock_bundle_dir(self, tmp_path):
        """Create mock bundle directory with various bundles."""
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()

        # Create various test bundles
        (bundle_dir / "ui-styles_assets_common.bundle").touch()
        (bundle_dir / "ui-styles_assets_default.bundle").touch()
        (bundle_dir / "ui-styles_assets_newgen.bundle").touch()
        (bundle_dir / "ui-styles_assets_regen.bundle").touch()
        (bundle_dir / "test_modified.bundle").touch()
        (bundle_dir / "test.bundle.bak").touch()
        (bundle_dir / "normal.bundle").touch()

        return bundle_dir

    def test_exclude_patterns_initialized(self, builder_with_exclusions):
        """Test that exclude patterns are properly initialized."""
        assert builder_with_exclusions.exclude_patterns == ["newgen", "regen"]

    def test_default_exclude_patterns(self, builder_without_exclusions):
        """Test that exclude patterns default to empty list."""
        assert builder_without_exclusions.exclude_patterns == []

    def test_expand_bundle_paths_with_exclusions(
        self, builder_with_exclusions, mock_bundle_dir
    ):
        """Test that user-provided exclusion patterns work."""
        bundles = builder_with_exclusions._expand_bundle_paths([mock_bundle_dir])

        # Should include common, default, and normal bundles
        bundle_names = [b.name for b in bundles]

        assert "ui-styles_assets_common.bundle" in bundle_names
        assert "ui-styles_assets_default.bundle" in bundle_names
        assert "normal.bundle" in bundle_names

        # Should exclude newgen and regen (user patterns)
        assert "ui-styles_assets_newgen.bundle" not in bundle_names
        assert "ui-styles_assets_regen.bundle" not in bundle_names

        # Should exclude default patterns
        assert "test_modified.bundle" not in bundle_names
        assert "test.bundle.bak" not in bundle_names

    def test_expand_bundle_paths_without_exclusions(
        self, builder_without_exclusions, mock_bundle_dir
    ):
        """Test that without exclusions, only default patterns are excluded."""
        bundles = builder_without_exclusions._expand_bundle_paths([mock_bundle_dir])

        bundle_names = [b.name for b in bundles]

        # Should include all non-default excluded bundles
        assert "ui-styles_assets_common.bundle" in bundle_names
        assert "ui-styles_assets_default.bundle" in bundle_names
        assert "ui-styles_assets_newgen.bundle" in bundle_names
        assert "ui-styles_assets_regen.bundle" in bundle_names
        assert "normal.bundle" in bundle_names

        # Should still exclude default patterns
        assert "test_modified.bundle" not in bundle_names
        assert "test.bundle.bak" not in bundle_names

    def test_case_insensitive_exclusion(self, tmp_path, mock_bundle_dir):
        """Test that exclusion patterns are case-insensitive."""
        icon_path = tmp_path / "icon.svg"
        icon_path.touch()

        # Create bundle with uppercase pattern
        (mock_bundle_dir / "ui-styles_NEWGEN_test.bundle").touch()

        builder = CatalogueBuilder(
            fm_version="2026.4.0",
            output_dir=tmp_path / "output",
            icon_white_path=icon_path,
            icon_black_path=icon_path,
            exclude_patterns=["newgen"],  # lowercase pattern
        )

        bundles = builder._expand_bundle_paths([mock_bundle_dir])
        bundle_names = [b.name for b in bundles]

        # Should exclude despite case difference
        assert "ui-styles_NEWGEN_test.bundle" not in bundle_names

    def test_single_bundle_file_exclusion(self, builder_with_exclusions, tmp_path):
        """Test that exclusion works for single bundle file paths."""
        # Create a single bundle file
        newgen_bundle = tmp_path / "newgen_test.bundle"
        newgen_bundle.touch()

        normal_bundle = tmp_path / "normal.bundle"
        normal_bundle.touch()

        # Test excluding newgen bundle
        bundles = builder_with_exclusions._expand_bundle_paths([newgen_bundle])
        assert len(bundles) == 0  # Should be excluded

        # Test including normal bundle
        bundles = builder_with_exclusions._expand_bundle_paths([normal_bundle])
        assert len(bundles) == 1  # Should be included
