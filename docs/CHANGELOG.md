# Changelog

All notable changes to FM Skin Builder will be documented in this file.

## [Unreleased]

### Added - November 4, 2024

#### ✅ UXML Export Modes (Phase 1.1)

**Three-tier export system for UXML files**:

- **MINIMAL Mode** (default):
  - Clean XML without comments
  - Binding data stored in `data-binding-*` attributes
  - 60% smaller file size vs VERBOSE
  - Optimized for editing and re-import
  - Example: `--export-mode minimal`

- **STANDARD Mode**:
  - Balanced view with helpful context
  - Template and component type comments
  - Limited inline binding comments (first 3)
  - Compact binding header (max 50 bindings)
  - Good for reference and documentation

- **VERBOSE Mode**:
  - Maximum detail for debugging
  - All comments preserved
  - Full binding header with details
  - All inline binding information
  - Unity internal structure notes

**Implementation**:
- Added `ExportMode` enum to `src/utils/uxml_parser.py`
- Updated `visual_tree_asset_to_xml()` with mode-aware generation
- Added `--export-mode` CLI argument to catalog builder
- Created comprehensive [docs/EXPORT_MODES.md](EXPORT_MODES.md)

**File Size Impact**:
- PlayerAttributesTile.uxml: 132 lines, 8.1 KB (MINIMAL) vs ~15-20 KB (VERBOSE)
- Full catalog (2,681 files): 30-50% space savings with MINIMAL

**Usage**:
```bash
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-tiles_assets_all.bundle \
  --export-files \
  --export-mode minimal  # or standard, verbose
```

**Related**:
- Roadmap: Phase 1.1 - COMPLETE ✅
- Next: Phase 1.2 - UXML Parser (XML → Unity structures)

---

### Added - November 3, 2024

#### 🎨 Asset Catalog & HTML Explorer

**Comprehensive asset cataloging system**:

- Scan Unity bundles for all asset types
- Extract metadata (dimensions, paths, bundles, PathIDs)
- Generate searchable JSON catalog
- Create interactive HTML explorer interface

**Asset Types Supported**:
- Backgrounds (Texture2D tagged with "background")
- Generic Textures (Texture2D)
- Sprites (with rect, pixelsPerUnit, pivot)
- Fonts (Font assets)
- Videos (VideoClip with frameCount, frameRate)
- CSS Variables & Classes (USS files)
- UXML Files (VisualTreeAsset with bindings)
- Stylesheets (StyleSheet with rules)

**Statistics**:
- 15,545 total searchable assets
- 2,681 UXML files with binding data
- 1,234 sprites with metadata
- 450+ CSS classes
- 300+ CSS variables

**HTML Explorer Features**:
- Instant client-side search and filtering
- Modern responsive UI with Tailwind CSS
- Click-to-copy asset names
- Asset metadata display
- Bundle and PathID information

**Implementation Files**:
- `scripts/build_css_uxml_catalog.py` - Main catalog builder
- `scripts/generate_asset_explorer.py` - HTML generator
- `src/utils/uxml_parser.py` - UXML/USS parsing
- `extracted_sprites/asset_explorer.html` - Interactive UI

**Documentation**:
- [docs/ASSET_CATALOG_IMPLEMENTATION.md](ASSET_CATALOG_IMPLEMENTATION.md)
- [docs/recipes/exporting_asset_catalogs.md](recipes/exporting_asset_catalogs.md)

**Usage**:
```bash
# Build catalog
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output extracted_sprites/css_uxml_catalog.json

# Generate explorer
PYTHONPATH=/workspaces/fm-skin-builder python scripts/generate_asset_explorer.py \
  --input extracted_sprites/css_uxml_catalog.json \
  --output extracted_sprites/asset_explorer.html
```

---

## Version History

### Pre-release (Before Changelog)

Initial development of FM Skin Builder with:
- CSS/USS patching system
- Bundle reading/writing
- Binding extraction
- Vector integration tests
- Basic skin format

---

## Future Additions

See [docs/ROADMAP_IMPORT_EXPORT.md](ROADMAP_IMPORT_EXPORT.md) for planned features:

### Phase 1: UXML Re-Import (In Progress)
- ✅ 1.1 Clean UXML Export Format - **COMPLETE**
- ⏳ 1.2 UXML Parser - Parse XML back to Unity structures
- ⏳ 1.3 Bundle Writer - Write modified assets to bundles
- ⏳ 1.4 Round-trip Validation - Ensure lossless conversions

### Phase 2: USS Import/Export
- USS to human-readable format
- USS parser and writer
- Variable preservation

### Phase 3: Advanced Binding Manipulation
- Visual binding editor
- Binding validation
- Automatic binding repair

### Phase 4: Complete UI Editor
- Visual UXML editor
- Live preview
- Component library
- Template system

---

## Notes

- UnityPy cleanup errors (`none_dealloc`) are expected during Python shutdown and can be ignored
- Hard exit mode (`FM_HARD_EXIT=1`) prevents these errors in production
- All exports use UTF-8 encoding with XML declaration
