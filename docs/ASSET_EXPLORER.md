# Asset Explorer & Catalog

**Searchable database of CSS variables, classes, UXML files, and their cross-references.**

## Quick Start

### 1. Build the Catalog

Scan bundles to extract CSS and UXML relationships:

```bash
# Scan UI style bundles (with file exports for preview)
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-styles_assets_common.bundle \
  --bundle bundles/ui-styles_assets_default.bundle \
  --bundle bundles/ui-panelids-uxml_assets_all.bundle \
  --output extracted_sprites/css_uxml_catalog.json \
  --export-files \
  --verbose

# Or scan entire bundle directory
python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output extracted_sprites/css_uxml_catalog.json \
  --export-files
```

**New in Phase 2.5**: Use `--export-files` to export human-readable USS (CSS) and UXML (XML) files for preview.

### 2. Generate HTML Explorer

Create a searchable web interface:

```bash
python scripts/generate_css_uxml_explorer.py \
  --input extracted_sprites/css_uxml_catalog.json \
  --output extracted_sprites/css_uxml_explorer.html
```

### 3. Browse

Open `extracted_sprites/css_uxml_explorer.html` in your browser.

### 4. Preview Files (Phase 2.5)

Click **🔍 Preview CSS** or **🔍 Preview XML** buttons on stylesheet/UXML cards to view full file contents with syntax highlighting.

See **[PREVIEW_FEATURE.md](./PREVIEW_FEATURE.md)** for detailed documentation.

---

## What It Does

The asset explorer answers questions like:

- **"Where is `--primary` defined?"** → Shows which stylesheets define it
- **"What uses `.green`?"** → Lists all UXML files using that class
- **"Which stylesheets use `--background`?"** → Cross-references variable usage
- **"What properties does `.button-primary` have?"** → Shows all CSS properties
- **"Show me the full CSS for SIStyles"** → 🔍 Click to preview (Phase 2.5)
- **"What's the XML structure of CalendarTool?"** → 🔍 Click to preview (Phase 2.5)

---

## Features

### 🔍 Search
- Real-time search across all assets
- Filter by name (variables, classes, files)
- Tab-based navigation (CSS Variables, CSS Classes, UXML Files, Stylesheets)

### 📊 Cross-References
- **CSS Variables**: Shows where defined and where used
- **CSS Classes**: Lists definitions, usage in UXML, and properties
- **UXML Files**: Shows stylesheet imports, classes used, inline styles
- **Stylesheets**: Lists all variables and classes defined

### 🎨 Rich Data
- Copy asset names to clipboard (click 📋)
- Expand/collapse detailed properties
- Color-coded tags for easy scanning
- Usage counts and statistics

---

## Catalog Structure

The JSON catalog has four main sections:

```json
{
  "css_variables": {
    "--primary": {
      "defined_in": ["CommonStyles.uss"],
      "used_in_stylesheets": ["DialogStyles", "ButtonStyles"],
      "used_in_uxml": ["MainMenu.uxml"],
      "value": "#00D3E7"
    }
  },
  "css_classes": {
    ".green": {
      "defined_in": ["colours/base.uss"],
      "used_in_uxml": ["PlayerCard.uxml"],
      "properties": {
        "color": [{"type": "color", "value": "#00D3E7"}]
      }
    }
  },
  "uxml_files": {
    "MainMenu.uxml": {
      "bundle": "ui-menus.bundle",
      "stylesheets": ["CommonStyles.uss"],
      "has_inline_styles": false,
      "classes_used": [".header", ".button"],
      "variables_used": ["--primary"],
      "elements": ["Button", "Label"]
    }
  },
  "stylesheets": {
    "CommonStyles": {
      "bundle": "ui-styles_assets_common.bundle",
      "variables_defined": ["--primary", "--background"],
      "classes_defined": [".header", ".button"],
      "properties": {
        ".header": [
          {"name": "color", "values": [{"type": "string", "value": "--primary"}]}
        ]
      }
    }
  }
}
```

---

## Use Cases

### 🎨 Skin Development
**Problem**: "I want to change the primary color, but where is it used?"

**Solution**:
1. Search for `--primary` in the explorer
2. See all stylesheets that define it
3. See all places that use it
4. Create CSS overrides in your skin

### 🔧 Debugging
**Problem**: "Why isn't my `.custom-class` working?"

**Solution**:
1. Search for `.custom-class` in the explorer
2. Check if it's defined in any stylesheet
3. See which UXML files already use it
4. Verify your class name matches exactly

### 📚 Documentation
**Problem**: "What classes are available for player cards?"

**Solution**:
1. Browse the "CSS Classes" tab
2. Filter by name (e.g., "player", "card")
3. See all properties for each class
4. Reference in your custom UXML/CSS

---

## Current Status

### ✅ Fully Working
- **CSS variable extraction and cross-referencing** - 547 variables tracked
- **CSS class detection and usage tracking** - 6,351 classes cataloged
- **UXML file parsing** - **1,283 UXML files discovered!** ✨
- **Real usage data** - See which UXML files use which CSS classes
- **Stylesheet scanning and property extraction** - Complete
- **Cross-references between stylesheets and UXML** - Fully functional

### 🎉 Major Discovery
FM26 stores UXML as `MonoBehaviour` objects with `m_VisualElementAssets` structure (Unity's VisualTreeAsset format). We've successfully:
- Detected all 1,283 UXML UI panel definitions
- Extracted CSS classes used in each panel
- Mapped element types (BindingRoot, SIText, VisualElement, etc.)
- Tracked inline style usage

**Most popular classes:**
- `.base-template-grow` - used in 352 UXML files
- `.row-direction-normal` - used in 182 UXML files
- `.flex-grow-class` - used in 87 UXML files
- `.body-regular-14px-regular` - used in 85 UXML files

### 🚧 Future Enhancements (Phase 3)
- **Backgrounds**: Image/texture reference tracking
- **Fonts**: Font usage detection
- **Videos**: Video asset cataloging
- **Sprites**: Integration with sprite extraction
- **CSS variable usage in UXML**: Detect var(--variable) references in inline styles

---

## Next Steps

### Phase 1: MVP ✅ COMPLETE
- [x] CSS ↔ UXML cross-reference tool
- [x] HTML explorer generation
- [x] Real bundle testing

### Phase 2: Enhanced UXML Parsing
- [ ] Improve UXML deserialization
- [ ] Better inline style detection
- [ ] Element hierarchy tracking
- [ ] Template references

### Phase 3: Full Asset Catalog
- [ ] Background/texture cataloging
- [ ] Font detection and usage
- [ ] Video asset tracking
- [ ] Sprite integration
- [ ] Visual relationship graphs

---

## Tips

### Performance
- Scanning many bundles takes time (~5-10s per bundle)
- Start with specific bundles (ui-styles, ui-panelids) for faster iteration
- Catalog JSON can be reused without re-scanning

### Best Bundles to Scan
- `ui-styles_assets_common.bundle` - Core CSS variables (6 stylesheets)
- `ui-styles_assets_default.bundle` - Main stylesheets (27 stylesheets)
- `ui-panelids-uxml_assets_all.bundle` - **722 UXML panel definitions** ⭐
- `ui-factoryxml_assets_all.bundle` - **561 UXML factory templates** ⭐

**Recommended scan command:**
```bash
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-styles_assets_common.bundle \
  --bundle bundles/ui-styles_assets_default.bundle \
  --bundle bundles/ui-panelids-uxml_assets_all.bundle \
  --bundle bundles/ui-factoryxml_assets_all.bundle \
  --output extracted_sprites/css_uxml_catalog.json \
  --verbose
```

### Search Tips
- Use partial names: `--global` finds all global variables
- Click tags to copy names for use in your CSS
- Use browser's Find (Ctrl+F) on expanded properties

---

## Technical Details

### CSS Variable Detection
Variables are detected from StyleSheet `strings` array. Any string starting with `--` is considered a CSS variable.

### CSS Class Detection
Classes are extracted from `m_ComplexSelectors` using the selector part builder. Covers `.class`, `#id`, `element`, and compound selectors.

### Property Extraction
Properties are parsed from `m_Rules.m_Properties.m_Values`:
- **Type 3/8/10**: String/variable references
- **Type 4**: Color values (converted to hex)
- **Type 1**: Numeric values

### Cross-Referencing
- **Variable usage**: Tracked when variables appear in property values
- **Class usage**: Tracked when classes appear in UXML `class="..."` attributes
- **Stylesheet imports**: Tracked from UXML `<Style src="..."/>` elements

---

## Examples

### Example 1: Finding a Color Variable

**Search**: `--primary`

**Result**:
```
Variable: --global-text-primary
├─ Defined in: SIStyles, IGEStyles, FigmaStyleVariables
├─ Used in CSS: 7 stylesheets
└─ Used in UXML: 3 files
```

### Example 2: Exploring a Class

**Search**: `.button-primary`

**Result**:
```
Class: .button-primary
├─ Defined in: ButtonStyles, CommonStyles
├─ Used in UXML: MainMenu, Settings, Dialog
└─ Properties:
    • background-color: --primary
    • border-radius: 4px
    • padding: 8px 16px
```

### Example 3: Checking UXML Dependencies

**Search**: `MainMenu`

**Result**:
```
UXML File: MainMenu.uxml
├─ Bundle: ui-menus.bundle
├─ Stylesheets: CommonStyles.uss, MenuStyles.uss
├─ Inline Styles: No
├─ Classes Used: .header, .button-primary, .menu-item
├─ Variables Used: --primary, --background
└─ Elements: Button (5), Label (3), ScrollView (1)
```

---

## Troubleshooting

### UXML Files Show Zero Usage
If you scanned bundles but UXML shows no usage data, make sure you're scanning the correct bundles:
- `ui-panelids-uxml_assets_all.bundle` - Contains 722 UXML panel definitions
- `ui-factoryxml_assets_all.bundle` - Contains 561 UXML factory templates
- These are stored as MonoBehaviour objects with `m_VisualElementAssets`

### Missing Variables
If you know a variable exists but don't see it:
- Ensure you scanned the correct bundle (try `--bundle-dir bundles`)
- Check that it's actually a CSS variable (starts with `--`)
- It might be defined inline in UXML (not yet detected)

### Slow Scanning
- Use `--bundle` to scan specific files instead of `--bundle-dir`
- Scanning 50+ bundles can take several minutes
- Consider scanning only UI-related bundles

---

## Credits

Built using:
- **UnityPy**: Unity asset deserialization
- **HTML/CSS/JS**: No dependencies, pure vanilla web tech
- Pattern inspired by `sprite_index.html`
