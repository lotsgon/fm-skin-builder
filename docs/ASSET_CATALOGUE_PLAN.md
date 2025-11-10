# Asset Catalogue System - Implementation Plan

**Status:** Ready for Implementation
**Created:** 2025-11-10
**FM Version Target:** 2026.x
**Estimated Duration:** 5 days

## Overview

Build a comprehensive asset catalogue system that extracts all game assets from Football Manager bundles and exports them in a searchable, web-friendly format for hosting on Cloudflare R2.

## Goals

Enable users to:
1. Search for CSS variables, classes, and their relationships
2. Browse sprites and textures with visual thumbnails
3. Find assets by color (perceptual color search)
4. Discover assets through auto-generated tags
5. Track changes between FM versions
6. Understand the internal structure (indices, stylesheets) for reverse engineering

## Key Features

### Data Extraction
- ✅ All CSS Variables with multi-value support
- ✅ All CSS Classes with property details
- ✅ Variable usage within classes (cross-references)
- ✅ Both resolved values (human-readable) AND raw Unity data
- ✅ String indices AND color indices for reverse engineering
- ✅ Stylesheet names (e.g., "FMColours")
- ✅ Background textures
- ✅ Sprite/icon files
- ✅ Vector sprite detection (has_vertex_data flag)
- ✅ Fonts

### Image Processing
- ✅ Thumbnail generation (256x256 WebP)
- ✅ Adaptive watermarking (white on dark, black on light)
  - Icon: bottom-right, 15% width, 30-40% opacity
  - Text: "FM Asset Preview" bottom center
  - Uses: `icons/SVG/White.svg` and `icons/SVG/Black.svg`
- ✅ Filename-based deduplication (wildcard matching)
  - `icon_player_16`, `icon_player_24` → ONE thumbnail
- ✅ Dominant color extraction (5 colors per image)

### Search Features
- ✅ Color-based search with perceptual similarity (LAB color space)
  - Find "similar purples" not just exact hex matches
- ✅ Auto-tagging from filenames
  - `icon_player_primary` → ["icon", "player", "person", "primary", "main"]
- ✅ Tag-based search across all asset types

### Version Tracking
- ✅ Track FM version (e.g., "2026.4.0")
- ✅ Track catalogue version (e.g., v2 = rebuild of same FM version)
- ✅ Asset lifecycle: added/removed/modified
- ✅ Keep removed assets with status="removed"
- ✅ Generate changelogs between versions

## Data Models

### CatalogueMetadata
```python
class CatalogueMetadata(BaseModel):
    catalogue_version: int           # e.g., 2 (rebuild version)
    fm_version: str                  # e.g., "2026.4.0" (game version)
    schema_version: str              # e.g., "1.0.0" (data format)
    generated_at: datetime
    bundles_scanned: List[str]
    total_assets: Dict[str, int]     # {"sprites": 2450, "textures": 820, ...}
    previous_fm_version: Optional[str]
    previous_catalogue_version: Optional[int]
    changes_since_previous: Optional[Dict[str, int]]
```

### CSSVariable
```python
class CSSVariable(BaseModel):
    name: str                        # "--primary-color"
    stylesheet: str                  # "FMColours" (Unity asset name)
    bundle: str                      # "skins.bundle"
    property_name: str               # "background-color"
    rule_index: int                  # Rule index in stylesheet

    # Multi-value support (Unity USS allows: --color: blue, red, green;)
    values: List[CSSValueDefinition]

    # Reverse engineering indices
    string_index: Optional[int]      # Index in strings array (type 3/8/10)
    color_index: Optional[int]       # Index in colors array (type 4)

    # Extracted colors for search
    colors: List[str]                # ["#1976d2"] (hex only)

    # Version tracking
    status: AssetStatus              # active | removed | modified
    first_seen: str                  # "2026.1.0"
    last_seen: str                   # "2026.4.0"
    modified_in: Optional[str]       # "2026.3.0"

class CSSValueDefinition(BaseModel):
    value_type: int                  # Unity type: 3=dimension, 4=color, 8=string, 10=variable
    index: int                       # Index in strings/colors array
    resolved_value: str              # "#1976d2" or "var(--primary)" or "10px"
    raw_value: Optional[Dict]        # {r: 0.098, g: 0.463, b: 0.824, a: 1.0} for colors
```

### CSSClass
```python
class CSSClass(BaseModel):
    name: str                        # ".button-primary"
    stylesheet: str                  # "FMColours"
    bundle: str
    properties: List[CSSProperty]    # All CSS properties in this class
    variables_used: List[str]        # ["--primary-color", "--button-bg"]
    tags: List[str]                  # ["button", "primary", "ui"]

    status: AssetStatus
    first_seen: str
    last_seen: str

class CSSProperty(BaseModel):
    name: str                        # "background-color"
    values: List[CSSValueDefinition] # Multi-value support

    @property
    def css_notation(self) -> str:
        """Render as CSS"""
        # Single value: "background-color: #1976d2;"
        # Multi-value: "background-color: #ff0000, #00ff00;"
```

### Sprite
```python
class Sprite(BaseModel):
    name: str                        # Primary name
    aliases: List[str]               # ["icon_player_16", "icon_player_24"]
    has_vertex_data: bool            # True = vector sprite (custom mesh data)
    content_hash: str                # SHA256 for integrity
    thumbnail_path: str              # "thumbnails/sprites/{hash}.webp"
    width: int
    height: int

    # Color palette (3-5 dominant colors)
    dominant_colors: List[str]       # ["#1976d2", "#ffffff", "#000000"]

    # Auto-tags
    tags: List[str]                  # ["icon", "player", "sport"]

    atlas: Optional[str]             # SpriteAtlas reference if applicable
    bundles: List[str]

    status: AssetStatus
    first_seen: str
    last_seen: str
```

### Texture
```python
class Texture(BaseModel):
    name: str
    aliases: List[str]
    content_hash: str
    thumbnail_path: str              # "thumbnails/textures/{hash}.webp"
    type: str                        # "background", "icon", "texture"
    width: int
    height: int
    dominant_colors: List[str]
    tags: List[str]
    bundles: List[str]

    status: AssetStatus
    first_seen: str
    last_seen: str
```

### Font
```python
class Font(BaseModel):
    name: str
    bundles: List[str]
    tags: List[str]

    status: AssetStatus
    first_seen: str
    last_seen: str
```

### AssetStatus
```python
class AssetStatus(str, Enum):
    ACTIVE = "active"      # Currently in game
    REMOVED = "removed"    # Was in game, now removed (kept in catalogue)
    MODIFIED = "modified"  # Changed between versions
```

## Storage Structure (R2)

```
/
├── latest.json                      # {"fm_version": "2026.4.0", "catalogue_version": 2}
├── versions.json                    # ["2026.0.0-v1", "2026.1.0-v1", "2026.4.0-v1", "2026.4.0-v2"]
├── changelog/
│   ├── 2026.3.0-to-2026.4.0-v1.json    # FM version upgrade
│   └── 2026.4.0-v1-to-v2.json          # Catalogue rebuild
│
└── 2026.4.0-v2/                     # FM version + catalogue version
    ├── metadata.json
    ├── css-variables.json
    ├── css-classes.json
    ├── sprites.json
    ├── textures.json
    ├── fonts.json
    ├── search-index.json            # Search optimization
    └── thumbnails/
        ├── sprites/
        │   └── a3f5d9e8c2b1.webp
        └── textures/
            └── b4e6c7d2f3a5.webp
```

### Why Split Files?
- Client-side partial loading (load only what's needed)
- Better caching (CSS changes don't invalidate sprite cache)
- Easier incremental updates

## Search Index Format

```json
{
  "color_palette": {
    "css_variables": {
      "#1976d2": ["--primary-color", "--link-color"],
      "#d32f2f": ["--error-color"]
    },
    "sprites": {
      "#ff0000": ["icon_player", "icon_team_red"],
      "#1976d2": ["icon_info", "icon_player"]
    },
    "textures": {
      "#00ff00": ["bg_grass", "bg_pitch"]
    }
  },

  "color_search": {
    "lab_colors": {
      "50_50_-50": ["--purple-color", "icon_purple_badge"]
    }
  },

  "tags": {
    "player": {
      "sprites": ["icon_player", "avatar_default"],
      "textures": ["bg_player_card"],
      "css_classes": [".player-card"]
    },
    "button": {
      "css_classes": [".button-primary", ".btn-submit"]
    }
  }
}
```

## Implementation Phases

### Phase 1: Core Extractors (Day 1)
**Files to create:**
- `fm_skin_builder/core/catalogue/extractors/base.py` - BaseAssetExtractor protocol
- `fm_skin_builder/core/catalogue/extractors/css_extractor.py` - Enhanced CSS extraction
- `fm_skin_builder/core/catalogue/extractors/sprite_extractor.py` - Sprite + vertex data
- `fm_skin_builder/core/catalogue/extractors/texture_extractor.py` - Texture extraction
- `fm_skin_builder/core/catalogue/extractors/font_extractor.py` - Font extraction
- `fm_skin_builder/core/catalogue/models.py` - Pydantic models

**Key Tasks:**
1. Extend bundle_inspector.py logic for CSS extraction
2. Extract full `m_Values` arrays (multi-value support)
3. Store both string_index AND color_index
4. Detect vector sprites: `has_vertex_data = getattr(sprite.m_RD.m_VertexData, 'm_VertexCount', 0) > 0`
5. Extract dominant colors from images (K-means clustering)
6. Generate auto-tags from filenames

### Phase 2: Image Processing (Day 2)
**Files to create:**
- `fm_skin_builder/core/catalogue/image_processor.py` - Thumbnails + watermarks
- `fm_skin_builder/core/catalogue/content_hasher.py` - SHA256 hashing
- `fm_skin_builder/core/catalogue/color_extractor.py` - Dominant color extraction

**Key Tasks:**
1. Thumbnail generation (256x256 WebP, maintain aspect ratio)
2. Brightness detection (calculate average luminance)
3. Adaptive watermark:
   - Load `icons/SVG/White.svg` or `icons/SVG/Black.svg` based on brightness
   - Render icon at bottom-right (15% of image width)
   - Add text "FM Asset Preview" at bottom center
   - 30-40% opacity for both
4. Extract 3-5 dominant colors using K-means clustering

### Phase 3: Search Index Builder (Day 2-3)
**Files to create:**
- `fm_skin_builder/core/catalogue/search_builder.py` - Build search indices
- `fm_skin_builder/core/catalogue/color_search.py` - LAB color space conversion
- `fm_skin_builder/core/catalogue/auto_tagger.py` - Filename → tags

**Key Tasks:**
1. Color palette aggregation across all assets
2. LAB color space conversion for perceptual similarity
3. Tag extraction using pattern matching:
   ```python
   PATTERNS = {
       'icon_': ['icon'],
       'bg_': ['background'],
       '_player': ['player', 'person'],
       'grass': ['grass', 'pitch', 'field']
   }
   ```
4. Build searchable indices

### Phase 4: Versioning & Diffing (Day 3)
**Files to create:**
- `fm_skin_builder/core/catalogue/version_differ.py` - Compare catalogues
- `fm_skin_builder/core/catalogue/changelog_generator.py` - Generate changelogs

**Key Tasks:**
1. Compare two catalogue versions by content hash
2. Track: added, removed, modified assets
3. Keep removed assets with `status="removed"`
4. Generate web-friendly changelogs:
   ```json
   {
     "summary": {
       "sprites_added": 15,
       "sprites_removed": 3,
       "css_variables_modified": 2
     },
     "details": {
       "added": {...},
       "removed": {...},
       "modified": [...]
     }
   }
   ```

### Phase 5: Aggregation & Export (Day 4)
**Files to create:**
- `fm_skin_builder/core/catalogue/aggregator.py` - Merge all bundles
- `fm_skin_builder/core/catalogue/deduplicator.py` - Filename wildcard matching
- `fm_skin_builder/core/catalogue/exporter.py` - R2-ready JSON export
- `fm_skin_builder/core/catalogue/builder.py` - Main orchestrator

**Key Tasks:**
1. Filename-based deduplication:
   ```python
   # Remove size suffixes: _16, _24, _32, @2x
   base = re.sub(r'_\d+x?\d*(@\dx)?$', '', name)
   # icon_player_16, icon_player_24 → icon_player
   ```
2. Aggregate data from all bundles
3. Export to split JSON files
4. Create directory structure for R2

### Phase 6: CLI Integration (Day 4)
**Files to create:**
- `fm_skin_builder/cli/commands/catalogue.py` - CLI command

**Key Tasks:**
1. Add `catalogue` subcommand to main.py
2. Implement flags:
   - `--bundle` (required): Bundle file or directory
   - `--out` (default: `build/catalogue`): Output directory
   - `--fm-version` (required): FM version string
   - `--compare-previous`: Path to previous catalogue for diffing
   - `--pretty`: Pretty-print JSON
   - `--dry-run`: Preview without writing
3. Progress reporting with rich library

### Phase 7: Testing (Day 5)
**Files to create:**
- `tests/test_catalogue_extractors.py`
- `tests/test_catalogue_images.py`
- `tests/test_catalogue_dedup.py`
- `tests/test_catalogue_search.py`
- `tests/test_catalogue_versioning.py`
- `tests/test_catalogue_integration.py`

**Key Tasks:**
1. Unit tests for each extractor
2. Image processing tests (watermark, colors)
3. Deduplication logic tests
4. Search index builder tests
5. Version differ tests
6. Full integration test with sample bundles

## Technical Implementation Details

### 1. Vertex Data Detection
```python
def has_vertex_data(sprite_obj) -> bool:
    """Check if sprite has custom vertex data (vector sprite)."""
    try:
        rd = getattr(sprite_obj, 'm_RD', None)
        if not rd:
            return False
        vertex_data = getattr(rd, 'm_VertexData', None)
        if not vertex_data:
            return False
        vertex_count = getattr(vertex_data, 'm_VertexCount', 0)
        return vertex_count > 0
    except:
        return False
```

### 2. Dominant Color Extraction
```python
from sklearn.cluster import KMeans
import numpy as np
from PIL import Image

def extract_dominant_colors(image_data: bytes, num_colors: int = 5) -> List[str]:
    img = Image.open(BytesIO(image_data)).convert('RGB')
    img = img.resize((150, 150))  # Faster processing

    pixels = np.array(img).reshape(-1, 3)
    kmeans = KMeans(n_clusters=num_colors, random_state=42)
    kmeans.fit(pixels)

    colors = kmeans.cluster_centers_.astype(int)
    labels = kmeans.labels_
    counts = np.bincount(labels)
    sorted_colors = [colors[i] for i in np.argsort(-counts)]

    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in sorted_colors]
```

### 3. LAB Color Space Search
```python
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

def find_similar_colors(target_hex: str, all_colors: Dict[str, List[str]], threshold: float = 20.0):
    """
    Find colors within perceptual distance using LAB color space.
    threshold=20 is "slightly different"
    threshold=50 is "noticeably different"
    """
    target_rgb = sRGBColor.new_from_rgb_hex(target_hex)
    target_lab = convert_color(target_rgb, LabColor)

    similar = []
    for hex_color, assets in all_colors.items():
        color_rgb = sRGBColor.new_from_rgb_hex(hex_color)
        color_lab = convert_color(color_rgb, LabColor)

        distance = delta_e_cie2000(target_lab, color_lab)
        if distance <= threshold:
            similar.extend(assets)

    return similar
```

### 4. Adaptive Watermark
```python
from PIL import Image, ImageDraw, ImageFont, ImageStat
import cairosvg

def apply_watermark(image: Image, icon_white: Path, icon_black: Path, opacity: float = 0.35):
    # Calculate brightness
    grayscale = image.convert('L')
    stat = ImageStat.Stat(grayscale)
    brightness = stat.mean[0] / 255.0

    # Choose icon color
    if brightness > 0.5:  # Light background
        icon_path = icon_black
        text_color = (0, 0, 0, int(255 * opacity))
    else:  # Dark background
        icon_path = icon_white
        text_color = (255, 255, 255, int(255 * opacity))

    # Load and render SVG icon
    icon_size = int(image.width * 0.15)
    icon_png = cairosvg.svg2png(
        url=str(icon_path),
        output_width=icon_size,
        output_height=icon_size
    )
    icon = Image.open(BytesIO(icon_png)).convert('RGBA')

    # Apply opacity to icon
    icon.putalpha(int(255 * opacity))

    # Paste icon at bottom-right
    x = image.width - icon_size - 10
    y = image.height - icon_size - 10
    image.paste(icon, (x, y), icon)

    # Add text
    draw = ImageDraw.Draw(image)
    text = "FM Asset Preview"
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (image.width - text_width) // 2
    text_y = image.height - 30
    draw.text((text_x, text_y), text, fill=text_color, font=font)

    return image
```

### 5. Filename Deduplication
```python
import re

def deduplicate_filenames(filenames: List[str]) -> Dict[str, List[str]]:
    """
    Group files using wildcard patterns.
    Returns: {primary_name: [aliases]}
    """
    groups = {}

    for name in filenames:
        # Remove size suffixes: _16, _24, _32, _48, _64, @2x, etc.
        base = re.sub(r'_\d+x?\d*(@\dx)?$', '', name)
        base = re.sub(r'@\dx$', '', base)

        if base not in groups:
            groups[base] = []
        groups[base].append(name)

    # Pick primary (base name if exists, else largest)
    results = {}
    for base, aliases in groups.items():
        if len(aliases) == 1:
            results[aliases[0]] = []
        else:
            primary = base if base in aliases else max(aliases, key=len)
            results[primary] = [a for a in aliases if a != primary]

    return results
```

### 6. Auto-Tagging
```python
import re

PATTERNS = {
    'icon_': ['icon'],
    'bg_': ['background'],
    'btn_': ['button', 'ui'],
    '_player': ['player', 'person'],
    '_team': ['team', 'club'],
    '_star': ['star', 'rating'],
    'grass': ['grass', 'pitch', 'field'],
    'primary': ['primary', 'main'],
    'secondary': ['secondary', 'alternate'],
}

def generate_tags(name: str) -> List[str]:
    """
    Extract tags from asset name.
    Example: "icon_player_primary" → ["icon", "player", "person", "primary", "main"]
    """
    tags = set()
    name_lower = name.lower()

    # Pattern matching
    for pattern, pattern_tags in PATTERNS.items():
        if pattern in name_lower:
            tags.update(pattern_tags)

    # Split on underscores/hyphens/camelCase
    parts = re.split(r'[_\-]|(?<=[a-z])(?=[A-Z])', name)
    tags.update(p.lower() for p in parts if len(p) > 2)

    return sorted(list(tags))
```

## CLI Usage Examples

### First Export
```bash
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles/ \
  --out build/catalogue \
  --fm-version "2026.4.0"

# Output:
# ✓ Scanned 75 bundles
# ✓ Found 2,450 sprites
#   - Extracted 2,450 thumbnails
#   - Deduplicated to 1,823 unique sprites
#   - Generated 12,250 color values
# ✓ Found 820 textures
#   - Extracted 820 thumbnails
#   - Deduplicated to 645 unique textures
# ✓ Found 245 CSS variables
# ✓ Found 1,205 CSS classes
# ✓ Found 18 fonts
# ✓ Generated 3,421 auto-tags
# ✓ Built search index
# ✓ Catalogue version: 1
# ✓ Output: build/catalogue/2026.4.0-v1/
```

### Rebuild (Fix Bug)
```bash
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles/ \
  --out build/catalogue \
  --fm-version "2026.4.0" \
  --compare-previous build/catalogue/2026.4.0-v1

# Output:
# ✓ Comparing against FM 2026.4.0-v1
# ✓ Catalogue version: 2 (rebuild)
# ✓ Changes: 0 added, 0 removed, 1 modified (icon_player hash corrected)
# ✓ Output: build/catalogue/2026.4.0-v2/
# ✓ Changelog: build/catalogue/changelog/2026.4.0-v1-to-v2.json
```

### New FM Version
```bash
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles/ \
  --out build/catalogue \
  --fm-version "2026.5.0" \
  --compare-previous build/catalogue/2026.4.0-v2

# Output:
# ✓ Comparing against FM 2026.4.0-v2
# ✓ Catalogue version: 1
# ✓ Changes:
#   - 15 sprites added
#   - 3 sprites removed (kept with status="removed")
#   - 2 sprites modified
#   - 12 CSS variables added
# ✓ Output: build/catalogue/2026.5.0-v1/
# ✓ Changelog: build/catalogue/changelog/2026.4.0-to-2026.5.0.json
```

### Dry Run
```bash
python -m fm_skin_builder.cli.main catalogue \
  --bundle bundles/ \
  --out build/catalogue \
  --fm-version "2026.5.0" \
  --dry-run

# Output:
# ✓ DRY RUN - No files will be written
# ✓ Would scan 75 bundles
# ✓ Would find ~2,450 sprites
# ✓ Would generate ~1,823 thumbnails
# ...
```

## Dependencies to Add

```txt
# requirements.txt additions
scikit-learn>=1.3.0        # K-means for color extraction
pillow>=10.0.0             # Image processing
cairosvg>=2.7.0            # SVG rendering
colormath>=3.0.0           # LAB color space
numpy>=1.24.0              # Array operations
```

## Future Enhancements (Not in Scope)

- R2 upload integration (CLI `--upload` flag)
- Perceptual hash deduplication (in addition to filename matching)
- UXML file extraction
- 3D texture/cubemap extraction
- Material extraction
- Audio clip extraction
- Incremental updates (delta exports)

## Success Criteria

- [ ] Successfully scans all FM bundles
- [ ] Extracts all required asset types
- [ ] Generates watermarked thumbnails
- [ ] Builds search indices
- [ ] Tracks version changes
- [ ] Exports R2-ready JSON files
- [ ] CLI commands work as documented
- [ ] All tests pass

## Notes

- Bundle scanning is for DEV purposes only (fresh FM install)
- Manual R2 upload initially (CLI integration later)
- Catalogue versioning is independent of FM version
- Removed assets are retained with status="removed"
- Multi-value CSS properties are exported (even if patching doesn't support yet)
- Color search uses LAB color space for perceptual similarity
- Deduplication uses filename wildcards (like existing texture swap system)

## Questions & Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Bundle scope | ALL bundles | Fresh install, dev purposes |
| CSS value format | Both raw + resolved | Reverse engineering + web display |
| Search metadata | Yes, include in Phase 1 | Color search + tags are core features |
| Deduplication | Filename wildcards | Simple, matches existing system |
| Watermark | Adaptive (white/black) | Legibility on all backgrounds |
| Version comparison | Local files | Dev workflow, no R2 needed yet |
| R2 upload | Manual (CLI later) | R2 doesn't exist yet |
| Multi-value export | Yes | Future-proof, low cost |
