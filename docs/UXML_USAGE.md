# UXML Import/Export Usage Guide

## Overview

The UXML system allows you to:
1. **Export** Unity UI layouts to clean, editable XML
2. **Modify** XML in any text editor
3. **Import** changes back to game bundles

## Current Capabilities

### ✅ What Works
- Export all 6,689 UXML files to XML
- Parse XML back to Unity structures
- Modify element integer fields (IDs, order, parent references)
- Save modified bundles

### ⚠️ Limitations
- String fields (Type, Name, Classes) are **read-only**
- Can't add/remove elements (only modify existing)
- Binding modifications not yet tested

## Quick Start

### 1. Export UXML

Export a specific UXML asset to XML:

```python
from src.core.bundle_manager import BundleManager
from src.utils.uxml_exporter import UXMLExporter

# Load bundle
manager = BundleManager()
manager.load_bundle("bundles/ui-tiles_assets_all.bundle")

# Export
exporter = UXMLExporter()
uxml_data = manager.get_uxml_asset("PlayerAttributesTile")
xml_content = exporter.export_to_xml(uxml_data, export_mode="MINIMAL")

# Save to file
with open("PlayerAttributesTile.uxml", "w") as f:
    f.write(xml_content)
```

### 2. Edit XML

Open the XML file in any text editor. The format is clean and intuitive:

```xml
<UXML>
  <VisualElement name="Root" class="tile-container">
    <Label text="Player Name" class="header" />
    <Label text="{player.name}" data-binding-path="person -> binding;player -> binding" />
  </VisualElement>
</UXML>
```

**Modify integer fields**:
- Element IDs (for advanced users)
- Parent-child relationships
- Document ordering

**Don't modify** (not yet supported):
- Element types (`<Label>`, `<VisualElement>`, etc.)
- Element/class names
- Adding/removing elements

### 3. Import Back

Import the modified XML into a bundle:

```python
from src.utils.uxml_binary_patcher import patch_uxml_from_xml

# Patch the bundle
success = patch_uxml_from_xml(
    bundle_path="bundles/ui-tiles_assets_all.bundle",
    asset_name="PlayerAttributesTile",
    xml_path="PlayerAttributesTile.uxml",
    output_path="build/ui-tiles_assets_all_modified.bundle",
    verbose=True
)

if success:
    print("✓ Bundle patched successfully!")
```

## Using with Skin System

Add UXML overrides to your skin's `config.json`:

```json
{
  "name": "My Custom Skin",
  "author": "Your Name",
  "uxml_overrides": {
    "PlayerAttributesTile": "uxml/PlayerAttributesTile.uxml"
  }
}
```

Directory structure:
```
skins/my_skin/
├── config.json
├── uxml/
│   └── PlayerAttributesTile.uxml
└── styles/
    └── custom.uss
```

## Technical Details

### How It Works

**Export** (Unity → XML):
1. UnityPy reads bundle and parses UXML asset
2. Extract element hierarchy and properties
3. Convert bindings from Unity's managed references to XML attributes
4. Generate clean XML with proper indentation

**Import** (XML → Unity):
1. Parse XML and reconstruct Unity data structures
2. Validate structure (IDs, references, bindings)
3. Load original bundle with UnityPy
4. **Get raw binary data** from asset (bypasses type tree)
5. Locate element offsets in binary by searching for IDs
6. Patch bytes directly with new values
7. Set modified binary back with `set_raw_data()`
8. Save bundle (no type tree serialization!)

### Why Binary Patching?

UnityPy's `save_typetree()` fails on UXML's `UnknownObject` types. We discovered that UnityPy objects expose `get_raw_data()` and `set_raw_data()` methods that operate on raw bytes, completely bypassing the broken type tree serialization path.

This allows us to:
- ✅ Modify UXML without hitting UnityPy limitations
- ✅ Preserve all Unity metadata automatically
- ✅ Work with any UnknownObject type
- ✅ Avoid complex type tree reconstruction

### Field Offsets

Elements are stored in Unity's binary format:

```
Offset  Size  Field
------  ----  -----
+0      4     m_Id (int32)
+4      4     m_OrderInDocument (int32)
+8      4     m_ParentId (int32)
+12     4     m_RuleIndex (int32)
...           (strings stored elsewhere)
```

## Examples

### Example 1: Reorder Elements

Change which elements appear first/last in the UI:

```xml
<!-- Before: Name label appears first (OrderInDocument: 0) -->
<Label name="NameLabel" m_OrderInDocument="0" />
<Label name="AgeLabel" m_OrderInDocument="1" />

<!-- After: Age label appears first -->
<Label name="AgeLabel" m_OrderInDocument="0" />
<Label name="NameLabel" m_OrderInDocument="1" />
```

### Example 2: Reparent Elements

Move an element to a different parent:

```xml
<!-- Before: Button is child of Panel1 -->
<VisualElement name="Panel1" m_Id="123">
  <Button name="MyButton" m_ParentId="123" />
</VisualElement>
<VisualElement name="Panel2" m_Id="456" />

<!-- After: Button is child of Panel2 -->
<VisualElement name="Panel1" m_Id="123" />
<VisualElement name="Panel2" m_Id="456">
  <Button name="MyButton" m_ParentId="456" />
</VisualElement>
```

## Troubleshooting

### "Asset not found in bundle"
- Check the asset name matches exactly (case-sensitive)
- Use `list_assets()` to see all available UXML assets

### "Could not locate element in raw data"
- Element structure might have changed
- Try re-exporting from the original bundle

### UnityPy errors on verification
- This is a known UnityPy cleanup issue
- If patching reported success, the file is valid

## Future Enhancements

Potential additions if needed:

1. **String Field Support**: Modify element types, names, and classes
   - Requires understanding Unity's string table format
   - Would enable adding custom CSS classes

2. **Binding Modifications**: Change data binding paths
   - Requires binary format analysis of managedReferencesRegistry
   - Would enable connecting UI to different data sources

3. **Add/Remove Elements**: Full structural changes
   - Most complex feature
   - Requires building entire UXML structure from scratch
   - May require Unity Editor for safety

## See Also

- `UXML_IMPORT_STATUS.md` - Technical implementation details
- `EXPORT_MODES.md` - UXML export format options
- `ARCHITECTURE.md` - Overall system architecture
