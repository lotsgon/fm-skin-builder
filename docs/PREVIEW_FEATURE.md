# Preview Feature - Phase 2.5

## Overview

The CSS & UXML Explorer now includes **click-to-preview** functionality for USS (CSS) and UXML (XML) files. This feature allows you to view the human-readable content of exported files directly within the explorer interface.

## What's New

### 1. Human-Readable Exports

All USS stylesheets and UXML files are now exported in human-readable formats:

- **USS files** → Exported as `.uss` (CSS format) in `extracted_sprites/exports/uss/`
- **UXML files** → Exported as `.uxml` (XML format) in `extracted_sprites/exports/uxml/`

### 2. Preview Buttons

Each stylesheet and UXML file card now includes a preview button:

- **🔍 Preview CSS** - For stylesheets
- **🔍 Preview XML** - For UXML files

### 3. Preview Modal

Clicking a preview button opens a modal overlay with:
- Syntax-highlighted code display
- Scrollable content area
- Close button (× in top-right)
- ESC key support to close

## Usage

### Step 1: Generate Catalog with Exports

Run the catalog builder with the `--export-files` flag:

```bash
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-styles_assets_common.bundle \
  --bundle bundles/ui-styles_assets_default.bundle \
  --bundle bundles/ui-panelids-uxml_assets_all.bundle \
  --bundle bundles/ui-factoryxml_assets_all.bundle \
  --output extracted_sprites/css_uxml_catalog.json \
  --export-files \
  --verbose
```

This creates:
- `extracted_sprites/exports/uss/*.uss` - USS stylesheets in CSS format
- `extracted_sprites/exports/uxml/*.uxml` - UXML files in XML format
- `extracted_sprites/css_uxml_catalog.json` - Catalog with export paths

### Step 2: Generate HTML Explorer

Generate the interactive HTML explorer:

```bash
python scripts/generate_css_uxml_explorer.py \
  --input extracted_sprites/css_uxml_catalog.json \
  --output extracted_sprites/css_uxml_explorer.html
```

### Step 3: Open in Browser

Open `extracted_sprites/css_uxml_explorer.html` in your web browser.

### Step 4: Preview Files

1. **Navigate** to the **UXML Files** or **Stylesheets** tab
2. **Find** the file you want to inspect (use the search box to filter)
3. **Click** the **🔍 Preview CSS** or **🔍 Preview XML** button
4. **View** the syntax-highlighted code in the modal
5. **Close** the preview by:
   - Clicking the × button
   - Pressing ESC
   - Clicking outside the preview modal

## Examples

### Previewing a Stylesheet

1. Go to **Stylesheets** tab
2. Search for "SIStyles"
3. Click **🔍 Preview CSS** on the SIStyles card
4. View the full CSS with syntax highlighting for:
   - Selectors (blue)
   - Properties (purple)
   - Values (green)

Example output:
```css
.ige-field {
    width: var(space-between);
    border-color: space-between;
    background-color: --colours-alpha-transparent-0;
}
```

### Previewing a UXML File

1. Go to **UXML Files** tab
2. Search for "CalendarTool"
3. Click **🔍 Preview XML** on the CalendarTool card
4. View the full XML structure with syntax highlighting for:
   - Tags (cyan)
   - Attributes (purple)
   - Strings (green)

Example output:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <UXML>
        <BindingRoot class="base-template-grow calendar-button-group">
            <BindingVariables class="base-template-grow">
                <!-- Element hierarchy -->
            </BindingVariables>
        </BindingRoot>
    </UXML>
</ui:UXML>
```

## Technical Details

### Export Process

**USS Export (`serialize_stylesheet_to_uss`)**:
- Converts Unity StyleSheet objects to USS format
- Preserves selectors (classes, IDs, type selectors)
- Exports properties with CSS variable references
- Handles pseudo-classes like `:hover`, `:focus`

**UXML Export (`visual_tree_asset_to_xml`)**:
- Reconstructs XML hierarchy from flat element array
- Uses `m_ParentId` to build parent-child relationships
- Preserves element names, classes, and properties
- Formats with proper indentation for readability

### File Organization

```
extracted_sprites/
├── exports/
│   ├── uss/                    # USS stylesheets
│   │   ├── FigmaStyleVariables.uss
│   │   ├── SIStyles.uss
│   │   ├── IGEStyles.uss
│   │   └── default.uss
│   └── uxml/                   # UXML files
│       ├── CalendarTool.uxml
│       ├── AboutClubCard.uxml
│       └── ... (722 files)
├── css_uxml_catalog.json
└── css_uxml_explorer.html
```

### Browser Compatibility

The preview feature uses:
- **Fetch API** - To load file content
- **Template literals** - For string manipulation
- **CSS Grid/Flexbox** - For responsive layout
- **ES6 features** - Arrow functions, const/let

Tested on:
- ✅ Chrome/Edge (Chromium-based)
- ✅ Firefox
- ✅ Safari

## Troubleshooting

### "File not found" Error

**Problem**: Preview shows "Error loading file: File not found"

**Solutions**:
1. Ensure you ran the catalog builder with `--export-files` flag
2. Check that `extracted_sprites/exports/` directory exists
3. Verify the HTML file is in the same directory as the exports folder
4. If using a web server, ensure it's serving the entire `extracted_sprites/` directory

### No Syntax Highlighting

**Problem**: Code displays but without colors

**Solutions**:
1. Clear browser cache and reload
2. Check browser console for JavaScript errors
3. Ensure you're using a modern browser (Chrome, Firefox, Safari)

### Preview Modal Won't Open

**Problem**: Clicking preview button does nothing

**Solutions**:
1. Check browser console for JavaScript errors
2. Ensure JavaScript is enabled in your browser
3. Try a different browser
4. Verify the HTML file was generated correctly

### Path Issues (File Protocol)

**Problem**: Preview works on a web server but not when opening HTML directly

**Solution**: Some browsers restrict `file://` protocol access. Options:
1. Use a local web server:
   ```bash
   python -m http.server 8000 --directory extracted_sprites/
   # Then open http://localhost:8000/css_uxml_explorer.html
   ```
2. Use VS Code "Live Server" extension
3. Use browser flags to allow local file access (not recommended for security)

## Future Enhancements

Potential improvements for Phase 3:

1. **Side-by-side comparison** - Compare two stylesheets or UXML files
2. **Download button** - Download individual files from preview
3. **Full-text search within files** - Search for specific properties or elements
4. **Diff viewer** - Show changes between original and modified files
5. **Image preview** - Show backgrounds, icons, and textures inline
6. **Interactive element tree** - Collapsible UXML element hierarchy
7. **CSS variable inspector** - Show variable definitions and usages with live preview

## Related Documentation

- [ASSET_EXPLORER.md](./ASSET_EXPLORER.md) - Full asset explorer documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [../README.md](../README.md) - Main project README
