#!/usr/bin/env python3
"""Test script for asset catalog functionality."""

from src.core.asset_catalog import AssetCatalog
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_asset_catalog():
    """Test asset catalog functionality."""
    print("=" * 80)
    print("ASSET CATALOG TEST")
    print("=" * 80)
    print()

    # Load test catalog
    catalog_path = Path("/tmp/test_asset_catalog_full.json")
    if not catalog_path.exists():
        print(f"ERROR: Test catalog not found at {catalog_path}")
        return False

    with open(catalog_path, 'r') as f:
        catalog = json.load(f)

    # Test 1: Verify structure
    print("TEST 1: Verify catalog structure")
    required_keys = ['css_variables', 'css_classes', 'uxml_files', 'stylesheets',
                     'backgrounds', 'textures', 'sprites', 'fonts', 'videos']

    for key in required_keys:
        if key in catalog:
            print(f"  ✓ {key}: {len(catalog[key])} items")
        else:
            print(f"  ✗ {key}: MISSING")
            return False
    print()

    # Test 2: Verify asset data completeness
    print("TEST 2: Verify asset data completeness")

    # Check backgrounds
    backgrounds = catalog.get('backgrounds', {})
    if backgrounds:
        sample_bg = list(backgrounds.values())[0]
        required_bg_fields = ['type', 'bundle', 'dimensions', 'path_id']
        for field in required_bg_fields:
            if field in sample_bg:
                print(f"  ✓ Background has '{field}'")
            else:
                print(f"  ✗ Background missing '{field}'")
                return False

    # Check sprites
    sprites = catalog.get('sprites', {})
    if sprites:
        sample_sprite = list(sprites.values())[0]
        required_sprite_fields = ['bundle', 'path_id']
        for field in required_sprite_fields:
            if field in sample_sprite:
                print(f"  ✓ Sprite has '{field}'")
            else:
                print(f"  ✗ Sprite missing '{field}'")
                return False
    print()

    # Test 3: Verify asset counts
    print("TEST 3: Verify asset counts")
    expected_min = {
        'backgrounds': 70,  # At least 70 backgrounds
        'sprites': 1000,    # At least 1000 sprites
        'css_variables': 100,  # At least 100 CSS variables
        'css_classes': 500,   # At least 500 CSS classes
        'uxml_files': 2000,   # At least 2000 UXML files
    }

    for key, min_count in expected_min.items():
        actual = len(catalog.get(key, {}))
        if actual >= min_count:
            print(f"  ✓ {key}: {actual} >= {min_count}")
        else:
            print(f"  ✗ {key}: {actual} < {min_count}")
            return False
    print()

    # Test 4: Verify cross-references exist
    print("TEST 4: Verify cross-reference fields")

    # Check if backgrounds have reference fields
    if backgrounds:
        sample_bg = list(backgrounds.values())[0]
        ref_fields = ['referenced_in_uxml', 'referenced_in_css']
        for field in ref_fields:
            if field in sample_bg:
                print(f"  ✓ Background has '{field}' field")
            else:
                print(f"  ✗ Background missing '{field}' field")
                return False
    print()

    # Test 5: Verify HTML explorer was generated
    print("TEST 5: Verify HTML explorer generation")
    html_path = Path(
        "/workspaces/fm-skin-builder/extracted_sprites/asset_explorer.html")
    if html_path.exists():
        size_mb = html_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ HTML explorer generated: {size_mb:.1f}MB")
    else:
        print(f"  ✗ HTML explorer not found")
        return False
    print()

    # Test 6: Sample data integrity
    print("TEST 6: Sample data integrity")

    # Check background dimensions
    bg_with_dims = 0
    for bg_name, bg_info in backgrounds.items():
        dims = bg_info.get('dimensions', {})
        if dims and dims.get('width') and dims.get('height'):
            bg_with_dims += 1
        if bg_with_dims >= 5:  # Check first 5
            break

    if bg_with_dims >= 5:
        print(f"  ✓ Backgrounds have valid dimensions")
    else:
        print(f"  ✗ Some backgrounds missing dimensions")
        return False

    # Check sprite dimensions
    sprite_with_dims = 0
    for sprite_name, sprite_info in sprites.items():
        dims = sprite_info.get('dimensions')
        if dims and dims.get('width') and dims.get('height'):
            sprite_with_dims += 1
        if sprite_with_dims >= 5:  # Check first 5
            break

    if sprite_with_dims >= 5:
        print(f"  ✓ Sprites have valid dimensions")
    else:
        print(f"  ✗ Some sprites missing dimensions")
        return False
    print()

    # Summary
    print("=" * 80)
    print("✓ ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("Asset Catalog Summary:")
    print(f"  • {len(catalog.get('backgrounds', {}))} backgrounds")
    print(f"  • {len(catalog.get('textures', {}))} textures")
    print(f"  • {len(catalog.get('sprites', {}))} sprites")
    print(f"  • {len(catalog.get('fonts', {}))} fonts")
    print(f"  • {len(catalog.get('videos', {}))} videos")
    print(f"  • {len(catalog.get('css_variables', {}))} CSS variables")
    print(f"  • {len(catalog.get('css_classes', {}))} CSS classes")
    print(f"  • {len(catalog.get('uxml_files', {}))} UXML files")
    print(f"  • {len(catalog.get('stylesheets', {}))} stylesheets")
    print()
    textures = catalog.get('textures', {})
    fonts = catalog.get('fonts', {})

    print("HTML Explorer:")
    print(f"  • Location: {html_path}")
    print(f"  • Size: {html_path.stat().st_size / (1024 * 1024):.1f}MB")
    print(f"  • Total searchable assets: {len(backgrounds) + len(textures) + len(sprites) + len(catalog.get('css_variables', {})) + len(catalog.get('css_classes', {})) + len(catalog.get('uxml_files', {})) + len(fonts)}")
    print()

    return True


if __name__ == "__main__":
    success = test_asset_catalog()
    sys.exit(0 if success else 1)
