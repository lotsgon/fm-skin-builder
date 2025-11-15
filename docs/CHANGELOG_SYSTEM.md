# Asset Catalogue Change Tracking System

## Overview

The FM Skin Builder asset catalogue now includes an automated change tracking system that compares catalogue versions and generates detailed changelogs. This helps skin creators understand what changed between FM versions.

## Features

### 1. Simplified Versioning

**Old System (v1.0):**
- Directory structure: `catalogue/2026.4.0-v1/`, `catalogue/2026.4.0-v2/`
- Multiple versions per FM release (v1, v2, v3...)
- Required manual version tracking

**New System (v2.0):**
- Directory structure: `catalogue/2026.4.0/`, `catalogue/2026.5.0/`
- One version per FM release
- Overwrites by default (no version counter)
- Simpler, cleaner structure

### 2. Automatic Change Detection

When building a new catalogue version, the system:
1. Detects if a previous FM version exists
2. Compares all assets between versions
3. Generates detailed changelog (JSON + HTML)
4. Updates metadata with change summary

### 3. Detailed Change Tracking

The system tracks changes for all asset types:

**CSS Variables:**
- Added variables
- Removed variables
- Modified values (color changes, dimension changes)
- Per-stylesheet breakdown

**CSS Classes:**
- Added classes
- Removed classes
- Modified properties
- CSS variable usage changes

**Sprites:**
- Added sprites
- Removed sprites
- Modified sprites (content hash comparison detects visual changes)
- Dimension changes
- Color palette changes

**Textures:**
- Added textures
- Removed textures
- Modified textures (content hash comparison)
- Dimension changes
- Color palette changes

**Fonts:**
- Added fonts
- Removed fonts

### 4. Per-Stylesheet Reports

CSS changes are organized by stylesheet for easy reference:
- `FMColours` changes
- `FMButtons` changes
- Custom stylesheet changes
- Variable-level and class-level detail

### 5. Notes System

Add contextual notes to catalogue versions:
```bash
# Add a note
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0 \
  --note "Fixed primary color to match new branding"

# Append additional notes
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0 \
  --note "Updated button sprites for better contrast" \
  --append

# View existing notes
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0
```

## CLI Commands

### Building Catalogues

```bash
# Build catalogue (automatically generates changelog if previous version exists)
python -m fm_skin_builder.cli.main catalogue \
  --bundle /path/to/fm/bundles \
  --fm-version "2026.5.0" \
  --out build/catalogue \
  --pretty
```

**Outputs:**
- `build/catalogue/2026.5.0/metadata.json` - Catalogue metadata
- `build/catalogue/2026.5.0/css-variables.json` - CSS variables
- `build/catalogue/2026.5.0/css-classes.json` - CSS classes
- `build/catalogue/2026.5.0/sprites.json` - Sprites
- `build/catalogue/2026.5.0/textures.json` - Textures
- `build/catalogue/2026.5.0/fonts.json` - Fonts
- `build/catalogue/2026.5.0/search-index.json` - Search index
- `build/catalogue/2026.5.0/changelog.json` - Change log (if previous version exists)
- `build/catalogue/2026.5.0/changelog.html` - HTML report (if previous version exists)
- `build/catalogue/2026.5.0/thumbnails/` - Thumbnail images

### Manual Diffing

Compare two specific catalogue versions:

```bash
python -m fm_skin_builder.cli.main catalogue-diff \
  --old build/catalogue/2026.4.0 \
  --new build/catalogue/2026.5.0 \
  --out build/changelog \
  --pretty
```

**Outputs:**
- `build/changelog/changelog.json` - Detailed JSON changelog
- `build/changelog/changelog.html` - Human-readable HTML report

### Managing Notes

```bash
# Add note
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0 \
  --note "Your note here"

# Append note
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0 \
  --note "Additional note" \
  --append

# View notes
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0
```

## Changelog Format

### JSON Structure

```json
{
  "from_version": "2026.4.0",
  "to_version": "2026.5.0",
  "generated_at": "2025-11-12T22:41:00Z",
  "summary": {
    "css_variable": {
      "added": 12,
      "removed": 3,
      "modified": 8,
      "total": 23
    },
    "css_class": {
      "added": 5,
      "removed": 2,
      "modified": 4,
      "total": 11
    },
    "sprite": {
      "added": 45,
      "removed": 2,
      "modified": 15,
      "total": 62
    },
    "texture": {
      "added": 20,
      "removed": 1,
      "modified": 5,
      "total": 26
    },
    "font": {
      "added": 1,
      "removed": 0,
      "modified": 0,
      "total": 1
    }
  },
  "changes_by_type": {
    "css_variable": {
      "added": [
        {
          "asset_type": "css_variable",
          "name": "--new-primary-color",
          "change_type": "added",
          "details": {
            "stylesheet": "FMColours",
            "property_name": "background-color",
            "values": "#1565c0",
            "colors": ["#1565c0"]
          }
        }
      ],
      "removed": [
        {
          "asset_type": "css_variable",
          "name": "--old-color",
          "change_type": "removed",
          "details": {
            "stylesheet": "FMColours",
            "property_name": "color",
            "values": "#cccccc"
          }
        }
      ],
      "modified": [
        {
          "asset_type": "css_variable",
          "name": "--primary-color",
          "change_type": "modified",
          "details": {
            "stylesheet": "FMColours",
            "property_name": "background-color",
            "old_values": "#1976d2",
            "new_values": "#1565c0",
            "old_colors": ["#1976d2"],
            "new_colors": ["#1565c0"]
          }
        }
      ]
    },
    "sprite": {
      "added": [...],
      "removed": [...],
      "modified": [
        {
          "asset_type": "sprite",
          "name": "icon_player",
          "change_type": "modified",
          "details": {
            "old_dimensions": "32x32",
            "new_dimensions": "64x64",
            "old_colors": ["#1976d2", "#ffffff"],
            "new_colors": ["#1565c0", "#f5f5f5"],
            "content_changed": true
          }
        }
      ]
    }
  },
  "changes_by_stylesheet": {
    "FMColours": {
      "css_variables": {
        "added": [...],
        "removed": [...],
        "modified": [...]
      },
      "css_classes": {
        "added": [...],
        "removed": [...],
        "modified": [...]
      }
    }
  },
  "notes": {
    "entries": [
      {
        "timestamp": "2025-11-12T22:41:00Z",
        "note": "Fixed primary color to match new branding"
      }
    ]
  }
}
```

### HTML Report

The HTML report provides a visual, browser-friendly view of all changes:
- Summary cards for each asset type
- Color-coded changes (green = added, red = removed, orange = modified)
- Per-stylesheet breakdown for CSS changes
- Color swatches for visual reference
- Detailed before/after comparisons

## Integration with Metadata

The catalogue metadata automatically includes change summaries:

```json
{
  "fm_version": "2026.5.0",
  "schema_version": "2.0.0",
  "generated_at": "2025-11-12T22:41:00Z",
  "bundles_scanned": ["skins.bundle", "fonts.bundle"],
  "total_assets": {
    "css_variables": 250,
    "css_classes": 180,
    "sprites": 1250,
    "textures": 520,
    "fonts": 12
  },
  "previous_fm_version": "2026.4.0",
  "changes_since_previous": {
    "css_variable": {"added": 12, "removed": 3, "modified": 8, "total": 23},
    "css_class": {"added": 5, "removed": 2, "modified": 4, "total": 11},
    "sprite": {"added": 45, "removed": 2, "modified": 15, "total": 62},
    "texture": {"added": 20, "removed": 1, "modified": 5, "total": 26},
    "font": {"added": 1, "removed": 0, "modified": 0, "total": 1}
  }
}
```

## Use Cases

### For Skin Creators

**Understanding FM Updates:**
```bash
# Build new catalogue when FM updates
python -m fm_skin_builder.cli.main catalogue \
  --bundle /path/to/fm2026.5/bundles \
  --fm-version "2026.5.0" \
  --out build/catalogue

# Review changelog.html in browser
open build/catalogue/2026.5.0/changelog.html
```

**Tracking Specific Changes:**
```bash
# Filter for color changes
cat build/catalogue/2026.5.0/changelog.json | \
  jq '.changes_by_type.css_variable.modified[] | select(.details.old_colors != .details.new_colors)'

# Find sprite modifications
cat build/catalogue/2026.5.0/changelog.json | \
  jq '.changes_by_type.sprite.modified[]'
```

**Adding Context:**
```bash
# Document why you rebuilt
python -m fm_skin_builder.cli.main catalogue-note \
  --catalogue-dir build/catalogue/2026.5.0 \
  --note "Rebuilt to include new DLC bundle assets"
```

### For Automated Workflows

**CI/CD Integration:**
```yaml
# GitHub Actions example
- name: Build catalogue and generate changelog
  run: |
    python -m fm_skin_builder.cli.main catalogue \
      --bundle bundles \
      --fm-version "${{ env.FM_VERSION }}" \
      --out catalogue

- name: Upload changelog as artifact
  uses: actions/upload-artifact@v4
  with:
    name: changelog-${{ env.FM_VERSION }}
    path: catalogue/${{ env.FM_VERSION }}/changelog.html
```

**API Integration:**
```python
import json

# Load changelog programmatically
with open('catalogue/2026.5.0/changelog.json') as f:
    changelog = json.load(f)

# Process changes
for change in changelog['changes_by_type']['sprite']['modified']:
    name = change['name']
    old_dims = change['details']['old_dimensions']
    new_dims = change['details']['new_dimensions']
    print(f"{name}: {old_dims} → {new_dims}")
```

## Migration from v1.0 to v2.0

### Breaking Changes

1. **Catalogue version removed:** The `--catalogue-version` flag no longer exists
2. **Directory structure changed:** No more `-vN` suffix
3. **Schema version updated:** Now `2.0.0` instead of `1.0.0`
4. **Metadata fields removed:** `catalogue_version` and `previous_catalogue_version` fields removed

### Migration Steps

**For CLI Users:**
```bash
# Old command
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles \
  --fm-version "2026.4.0" \
  --catalogue-version 2 \
  --out catalogue

# New command (remove --catalogue-version)
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles \
  --fm-version "2026.4.0" \
  --out catalogue
```

**For Scripts:**
```bash
# Old: upload_catalogue_to_r2.py required --catalogue-version
python scripts/upload_catalogue_to_r2.py \
  --catalogue-dir build/catalogue/2026.4.0-v1 \
  --fm-version "2026.4.0" \
  --catalogue-version 1

# New: --catalogue-version removed
python scripts/upload_catalogue_to_r2.py \
  --catalogue-dir build/catalogue/2026.4.0 \
  --fm-version "2026.4.0"
```

**For Code:**
```python
# Old
from fm_skin_builder.core.catalogue.models import CatalogueMetadata
metadata = CatalogueMetadata(
    catalogue_version=1,
    fm_version="2026.4.0",
    total_assets={}
)

# New
metadata = CatalogueMetadata(
    fm_version="2026.4.0",
    total_assets={}
)
```

## Technical Details

### Change Detection Algorithm

**Content-Based (Sprites/Textures):**
- Uses SHA256 content hashing
- Detects visual changes automatically
- Compares dimensions and color palettes

**Value-Based (CSS):**
- Compares resolved values
- Detects color changes
- Tracks variable dependencies

**Name-Based (Fonts):**
- Simple presence/absence detection

### Performance

**Changelog Generation:**
- Typically completes in < 5 seconds
- Scales linearly with asset count
- Minimal memory overhead

**Storage:**
- changelog.json: ~50-500 KB (depending on changes)
- changelog.html: ~100-1000 KB (includes inline CSS)

## Troubleshooting

### No changelog generated

**Issue:** Catalogue builds successfully but no `changelog.json` created.

**Solution:**
- Ensure a previous version exists in the same output directory
- Check that the previous version is named differently (e.g., `2026.4.0` vs `2026.5.0`)

### Changelog shows no changes

**Issue:** Changelog generated but shows 0 changes for all asset types.

**Possible causes:**
- Comparing identical catalogues
- Previous version corrupted or incomplete

**Solution:**
- Verify both catalogues have all required JSON files
- Compare manually: `diff -r catalogue/2026.4.0 catalogue/2026.5.0`

### Missing CSS file details

**Issue:** Changelog doesn't show per-stylesheet breakdown.

**Solution:**
- This is expected if no CSS changes occurred
- Check `changes_by_stylesheet` in JSON for empty objects

## Future Enhancements

Potential improvements for future versions:
- [ ] Visual diff images for sprites/textures
- [ ] Semantic version comparison (major/minor changes)
- [ ] Change impact analysis (used by X skins)
- [ ] RSS feed generation for change notifications
- [ ] Integration with FM modding forums/Discord

## Support

For issues or questions:
- GitHub Issues: https://github.com/lotsgon/fm-skin-builder/issues
- Documentation: https://github.com/lotsgon/fm-skin-builder/tree/main/docs
