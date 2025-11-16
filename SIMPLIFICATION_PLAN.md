# Catalogue Model Simplification Plan

## Executive Summary

Analysis shows significant bloat across all catalogue models. Many fields are never used by search indexes, dependency graphs, or website rendering. This plan identifies what to keep vs remove for optimal file size and maintainability.

---

## 1. CSS Variables

### Current Model (Bloated)
```json
{
  "name": "--scroller-size",
  "stylesheet": "BindingInspector",
  "bundle": "debugassets_assets_all.bundle",
  "property_name": "--scroller-size",        // ❌ NEVER USED
  "rule_index": 0,                          // ❌ NEVER USED
  "values": [                               // ❌ COMPLEX, ONLY values[0].resolved_value USED
    {
      "value_type": 3,
      "index": 0,
      "resolved_value": "row",
      "raw_value": null
    }
  ],
  "string_index": 0,                        // ❌ NEVER USED
  "color_index": null,                      // ❌ NEVER USED
  "colors": ["#1976d2"],                    // ✅ USED (color palette search)
  "status": "active",
  "first_seen": "2026.0.4",
  "last_seen": "2026.0.4"
}
```

### Proposed Model (Simplified)
```json
{
  "name": "--scroller-size",
  "value": "row",                           // ✅ Simple string
  "stylesheet": "BindingInspector",         // ✅ USED (variable definitions index)
  "bundle": "debugassets_assets_all.bundle", // ✅ USED (variable definitions index)
  "colors": ["#1976d2"],                    // ✅ USED (color palette search)
  "status": "active",
  "first_seen": "2026.0.4",
  "last_seen": "2026.0.4",
  "change_status": "new",                   // ✅ USED (change index)
  "changed_in_version": "2026.0.4",
  "previous_value": null
}
```

### Fields to Remove
- ❌ `property_name` - Never accessed
- ❌ `rule_index` - Never accessed
- ❌ `values: List[CSSValueDefinition]` - Only `values[0].resolved_value` is used, replace with simple `value: str`
- ❌ `string_index` - Unity reverse engineering metadata, never used
- ❌ `color_index` - Unity reverse engineering metadata, never used
- ❌ `modified_in` - Replaced by `change_status` + `changed_in_version`
- ❌ `previous_values` - Rename to `previous_value` (singular)

### Code Changes Required
- **css_extractor.py**: Simplify `_create_css_variable()` to extract single value string
- **css_resolver.py**: Update `build_variable_registry()` to use `var.value` instead of `var.values[0].resolved_value`
- **dependency_graph.py**: Update variable dependency extraction to search `var.value` for var() references
- **models.py**: Update CSSVariable model
- **Tests**: Update all variable-related tests

**File Size Reduction**: ~60% for CSS variables

---

## 2. CSS Classes

### Current Model (Already Simplified)
```json
{
  "name": ".my-class",
  "stylesheet": "FMColours",
  "bundle": "skins.bundle",
  "raw_properties": {                       // ✅ USED (search by property name)
    "border-color": "var(--my-color)",
    "opacity": "0.9"
  },
  "resolved_properties": {                  // ❌ NEVER READ
    "border-color": "#1976d2",
    "opacity": "0.9"
  },
  "asset_dependencies": ["icon_player"],    // ✅ USED (search by asset)
  "variables_used": ["--my-color"],         // ✅ USED (dependency graphs, search)
  "color_tokens": ["#1976d2"],              // ✅ USED (color search)
  "numeric_tokens": ["0.9"],                // ✅ USED (token search)
  "summary": {...},                         // ❌ NEVER READ
  "tags": ["panel"],                        // ✅ USED (tag search)
  "status": "active",
  "first_seen": "2026.1.0",
  "last_seen": "2026.4.0"
}
```

### Proposed Model (Further Simplified)
```json
{
  "name": ".my-class",
  "stylesheet": "FMColours",
  "bundle": "skins.bundle",
  "raw_properties": {                       // ✅ KEEP
    "border-color": "var(--my-color)",
    "opacity": "0.9"
  },
  "asset_dependencies": ["icon_player"],    // ✅ KEEP
  "variables_used": ["--my-color"],         // ✅ KEEP
  "color_tokens": ["#1976d2"],              // ✅ KEEP
  "numeric_tokens": ["0.9"],                // ✅ KEEP
  "tags": ["panel"],                        // ✅ KEEP
  "status": "active",
  "first_seen": "2026.1.0",
  "last_seen": "2026.4.0",
  "change_status": "modified",
  "changed_in_version": "2026.1.0",
  "previous_properties": {...}              // ✅ KEEP (for diffs)
}
```

### Fields to Remove
- ❌ `resolved_properties` - Only set, never read anywhere in codebase
- ❌ `summary` - Only set, never read anywhere in codebase

### Code Changes Required
- **models.py**: Remove `resolved_properties` and `summary` fields
- **css_extractor.py**: Stop setting these fields in `_enhance_classes_with_resolution()`
- **css_resolver.py**: Stop returning resolved_properties, update `resolve_css_class_properties()` signature
- **Tests**: Update tests to not check for these fields

**File Size Reduction**: ~30% for CSS classes

---

## 3. Sprites

### Current Model
```json
{
  "name": "icon_player",
  "aliases": ["icon_player_16", "icon_player_24"], // ✅ USED (merged during dedup)
  "has_vertex_data": false,                 // ❓ QUESTIONABLE VALUE
  "content_hash": "abc123...",              // ✅ USED (deduplication, integrity)
  "thumbnail_path": "thumbnails/sprites/abc123.webp", // ✅ USED (website display)
  "width": 24,                              // ❓ MIGHT BE USEFUL
  "height": 24,                             // ❓ MIGHT BE USEFUL
  "dominant_colors": ["#1976d2"],           // ✅ USED (color palette search)
  "tags": ["icon", "player"],               // ✅ USED (tag search)
  "atlas": "IconAtlas",                     // ❓ MIGHT BE USEFUL
  "bundles": ["ui.bundle"],                 // ✅ USEFUL (know where it came from)
  "status": "active",
  "first_seen": "2026.1.0",
  "last_seen": "2026.4.0"
}
```

### Analysis
**Keep:**
- ✅ `name`, `aliases` - Essential
- ✅ `content_hash` - Used for deduplication
- ✅ `thumbnail_path` - Website display
- ✅ `dominant_colors` - Color search
- ✅ `tags` - Tag search
- ✅ `bundles` - Source tracking
- ✅ Version tracking fields

**Questionable (User Decision):**
- ❓ `has_vertex_data` - Only useful if website shows "vector vs bitmap" badge
- ❓ `width`, `height` - Only useful if website shows dimensions or filters by size
- ❓ `atlas` - Only useful if website shows sprite atlas groupings

**Recommendation**: Keep all fields unless user confirms they won't display dimensions/atlas info on website.

---

## 4. Textures

### Current Model
```json
{
  "name": "bg_default",
  "aliases": [],                            // ✅ USED (merged during dedup)
  "content_hash": "def456...",              // ✅ USED (deduplication, integrity)
  "thumbnail_path": "thumbnails/textures/def456.webp", // ✅ USED (website display)
  "type": "background",                     // ❓ MIGHT BE USEFUL (filter by type)
  "width": 1920,                            // ❓ MIGHT BE USEFUL (filter by size)
  "height": 1080,                           // ❓ MIGHT BE USEFUL (filter by size)
  "dominant_colors": ["#000000"],           // ✅ USED (color palette search)
  "tags": ["background", "dark"],           // ✅ USED (tag search)
  "bundles": ["backgrounds.bundle"],        // ✅ USEFUL (know where it came from)
  "status": "active",
  "first_seen": "2026.1.0",
  "last_seen": "2026.4.0"
}
```

### Analysis
Same as Sprites - all fields are reasonable. The questionable ones (`type`, `width`, `height`) depend on whether the website will have filtering/display for these.

**Recommendation**: Keep all fields unless user confirms they won't show dimensions/type on website.

---

## 5. Fonts

### Current Model (Already Minimal)
```json
{
  "name": "Roboto-Regular",
  "bundles": ["fonts.bundle"],              // ✅ Source tracking
  "tags": ["sans-serif", "ui"],             // ✅ USED (tag search)
  "status": "active",
  "first_seen": "2026.1.0",
  "last_seen": "2026.4.0"
}
```

### Analysis
Already minimal - nothing to remove!

---

## Implementation Priority

### Phase 1: High Impact (Do First)
1. **CSS Variables** - Biggest bloat, easiest win
   - Remove: `property_name`, `rule_index`, `values` (complex), `string_index`, `color_index`
   - Add: `value` (simple string)
   - **Impact**: ~60% size reduction

2. **CSS Classes** - Remove unused fields
   - Remove: `resolved_properties`, `summary`
   - **Impact**: ~30% size reduction

### Phase 2: User Decision Required
3. **Sprites** - Ask user about:
   - Keep `has_vertex_data`?
   - Keep `width`/`height`?
   - Keep `atlas`?

4. **Textures** - Ask user about:
   - Keep `type`?
   - Keep `width`/`height`?

---

## Expected Results

### Before (Current)
```
CSS Variables:    ~500 KB per 1000 variables
CSS Classes:      ~800 KB per 1000 classes
Total for typical catalogue: ~15-20 MB
```

### After (Simplified)
```
CSS Variables:    ~200 KB per 1000 variables (-60%)
CSS Classes:      ~560 KB per 1000 classes (-30%)
Total for typical catalogue: ~8-12 MB (-40-45% overall)
```

---

## Questions for User

1. **Sprites**: Do you need `has_vertex_data`, `width`, `height`, `atlas` on the website?
2. **Textures**: Do you need `type`, `width`, `height` on the website?
3. **Change Tracking**: Keep the change tracking fields (`change_status`, `changed_in_version`, `previous_*`)? These are useful for version comparison but add bulk.

---

## Rollout Plan

1. Implement CSS Variable simplification
2. Implement CSS Class simplification
3. Get user feedback on Sprite/Texture fields
4. Implement Sprite/Texture changes (if any)
5. Run full test suite
6. Commit and push
7. Build test catalogue and verify JSON size reduction
