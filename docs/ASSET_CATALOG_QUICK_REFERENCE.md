# Asset Catalog Quick Reference

## 🚀 Quick Start

### Build Complete Catalog (First Time or Update)
```bash
cd /workspaces/fm-skin-builder

# Build catalog from all bundles (~5-10 minutes)
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output extracted_sprites/css_uxml_catalog.json

# Generate HTML explorer
PYTHONPATH=/workspaces/fm-skin-builder python scripts/generate_asset_explorer.py \
  --input extracted_sprites/css_uxml_catalog.json \
  --output extracted_sprites/asset_explorer.html

# Open in browser
$BROWSER extracted_sprites/asset_explorer.html
```

### Quick Test (Fast)
```bash
# Build catalog from just a few key bundles (~60 seconds)
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-tiles_assets_all.bundle \
  --bundle bundles/ui-styles_assets_common.bundle \
  --bundle bundles/ui-backgrounds_assets_common.bundle \
  --bundle bundles/ui-icons_assets_1x.bundle \
  --output /tmp/quick_catalog.json

# Generate explorer
PYTHONPATH=/workspaces/fm-skin-builder python scripts/generate_asset_explorer.py \
  --input /tmp/quick_catalog.json \
  --output /tmp/asset_explorer.html
```

## 📦 What Gets Cataloged

### Asset Types
- **Backgrounds** - Large textures (≥512px) like boardrooms, offices
- **Textures** - Small textures (<512px) like UI elements
- **Sprites** - Icons, buttons, graphics (1,560+ found)
- **Fonts** - TrueType and SDF fonts
- **Videos** - Video clips (rare)

### CSS/UXML Data
- **CSS Variables** - All `--variable-name` declarations (553 found)
- **CSS Classes** - All `.class-name` selectors (8,303 found)
- **UXML Files** - All UI layout files (6,689 found)
- **Stylesheets** - USS files with rules

### Metadata Captured
```json
{
  "AssetName": {
    "type": "Texture2D",
    "bundle": "ui-backgrounds_assets_common",
    "dimensions": {"width": 2048, "height": 1024},
    "format": 28,
    "path_id": -9104996263240036378,
    "referenced_in_uxml": [],
    "referenced_in_css": []
  }
}
```

## 🔍 Using the HTML Explorer

### Features
1. **Search Bar** - Type to filter assets instantly
2. **Tabs** - Click tabs to filter by type (CSS, UXML, Images, Fonts)
3. **Asset Cards** - Hover for details, click name to copy
4. **Statistics** - Dashboard shows asset counts at a glance

### Search Tips
- Search by name: `background`, `icon`, `button`
- Search CSS: `--primary`, `.heading`
- Search UXML: `MainMenu`, `PlayerCard`
- Case-insensitive, partial matches work

### Copying Names
- Click any blue asset name
- Name is copied to clipboard
- Toast notification confirms

## 🛠️ Advanced Usage

### Single Bundle
```bash
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-backgrounds_assets_common.bundle \
  --output backgrounds_catalog.json
```

### Multiple Specific Bundles
```bash
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-styles_assets_common.bundle \
  --bundle bundles/ui-backgrounds_assets_common.bundle \
  --bundle bundles/ui-icons_assets_1x.bundle \
  --output custom_catalog.json
```

### With File Export
```bash
# Also exports USS and UXML to extracted_sprites/exports/
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output extracted_sprites/css_uxml_catalog.json \
  --export-files
```

### Verbose Logging
```bash
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output catalog.json \
  --verbose
```

## 🧪 Testing

```bash
# Run test suite
python test_asset_catalog.py

# Expected output
✓ ALL TESTS PASSED
Asset Catalog Summary:
  • 79 backgrounds
  • 1560 sprites
  • ... (more stats)
```

## 📊 Expected Results

### From Full Catalog (all bundles)
```
Assets:
  Backgrounds: ~100
  Textures: ~500
  Sprites: ~5,000
  Fonts: ~10
  Videos: ~5

CSS/UXML:
  CSS Variables: ~550
  CSS Classes: ~8,000
  UXML Files: ~6,700
  Stylesheets: ~50

Total: ~21,000+ searchable assets
```

### File Sizes
- Catalog JSON: ~40MB
- HTML Explorer: ~25-30MB
- Both are self-contained, no dependencies

## 🔧 Troubleshooting

### "Fatal Python error: none_dealloc"
This is a UnityPy cleanup issue at script end. **Ignore it** - the catalog was built successfully. The error happens after all work is done.

### Catalog is missing assets
Make sure you're scanning bundles that contain those assets:
- Backgrounds: `ui-backgrounds_assets_common.bundle`
- Icons: `ui-icons_assets_1x.bundle`, `ui-icons_assets_2x.bundle`
- UXML: `ui-tiles_assets_all.bundle`, `ui-panels_assets_all.bundle`
- CSS: `ui-styles_assets_common.bundle`, `ui-styles_assets_default.bundle`

### HTML explorer is slow
With 21K+ assets, initial load takes 2-3 seconds. After that, search is instant. This is normal.

### Need to rebuild catalog
Only rebuild when:
- FM releases new bundles
- You modify bundle files
- Testing new features

Otherwise, reuse existing catalog.

## 📁 File Locations

```
/workspaces/fm-skin-builder/
├── src/core/asset_catalog.py              # Core implementation
├── scripts/
│   ├── build_css_uxml_catalog.py          # Catalog builder
│   └── generate_asset_explorer.py         # HTML generator
├── extracted_sprites/
│   ├── css_uxml_catalog.json              # Generated catalog
│   ├── asset_explorer.html                # Generated explorer
│   └── exports/                           # Optional USS/UXML exports
│       ├── uss/                           # Exported stylesheets
│       └── uxml/                          # Exported layouts
└── test_asset_catalog.py                  # Test suite
```

## 📚 Documentation

- `docs/ASSET_CATALOG_IMPLEMENTATION.md` - Full technical details
- `docs/ASSET_CATALOG_COMPLETE.md` - Implementation summary
- `docs/ROADMAP_IMPORT_EXPORT.md` - Future plans
- `docs/BINDING_EXTRACTION.md` - UXML bindings

## 💡 Tips

1. **First Time Setup**
   - Run full catalog build once: ~10 minutes
   - Generates 40MB JSON + 25MB HTML
   - Keep these files, reuse them

2. **Daily Usage**
   - Just open `asset_explorer.html`
   - No rebuild needed unless bundles change
   - Instant search, works offline

3. **Finding Assets**
   - Use search for quick lookups
   - Use tabs to browse by category
   - Click names to copy for use in code

4. **Performance**
   - Initial load: 2-3 seconds
   - Search: <50ms
   - Filter by tab: instant
   - No server or database needed

## 🎯 Common Use Cases

### Find a Background
1. Open `asset_explorer.html`
2. Click "Backgrounds" tab
3. Search for name (e.g., "office")
4. Click to copy exact name

### Check CSS Variable Usage
1. Open explorer
2. Click "CSS Variables" tab
3. Search for variable (e.g., "--primary")
4. See which stylesheets define it
5. See which UXML files use it

### Browse All Sprites
1. Open explorer
2. Click "Sprites" tab
3. Scroll or search
4. See dimensions and bundle location

### Validate Asset Exists
1. Search for asset name
2. If found, get PathID and bundle
3. Use for re-import operations

## 🚀 Next Steps

Now that you have the asset catalog:

1. **Explore** - Open HTML explorer, browse assets
2. **Plan Mods** - Identify which assets to modify
3. **Document** - Reference asset names/IDs in your notes
4. **Prepare Import** - PathIDs ready for future re-import feature

The catalog provides the foundation for **Phase 1: UXML Re-Import** (see `docs/ROADMAP_IMPORT_EXPORT.md`).

---

**Quick Links:**
- HTML Explorer: `extracted_sprites/asset_explorer.html`
- Full Docs: `docs/ASSET_CATALOG_IMPLEMENTATION.md`
- Test Suite: `python test_asset_catalog.py`
