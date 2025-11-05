# Testing UXML Changes In-Game

## Quick Start - Test Single Bundle

The easiest way to test UXML changes:

```bash
# Build a single bundle with UXML override
python build_uxml_test.py
```

This creates: `build/ui-tiles_assets_all_modified.bundle` (40MB)

**Output includes:**
- Source bundle: `bundles/ui-tiles_assets_all.bundle`
- UXML override: `skins/test_uxml_import/uxml/PlayerAttributesTile.uxml`
- Modified bundle with all 36 elements patched

## Installing in Football Manager

### Option 1: Replace Original Bundle (Backup First!)

```bash
# Find your FM installation
# Common locations:
# - Steam: ~/.steam/steam/steamapps/common/Football Manager 2024/
# - macOS: ~/Library/Application Support/Steam/steamapps/common/Football Manager 2024/

# Backup original
cp "/path/to/FM24/data/ui-tiles_assets_all.bundle" \
   "/path/to/FM24/data/ui-tiles_assets_all.bundle.backup"

# Install modified bundle
cp build/ui-tiles_assets_all_modified.bundle \
   "/path/to/FM24/data/ui-tiles_assets_all.bundle"
```

### Option 2: Use FM's Skin System (Recommended)

If FM supports loading modified bundles through the skin system:

```bash
# Copy to FM user data skins folder
# Location varies by platform:
# - Windows: Documents/Sports Interactive/Football Manager 2024/skins/
# - macOS: ~/Library/Application Support/Sports Interactive/Football Manager 2024/skins/
# - Linux: ~/.local/share/Sports Interactive/Football Manager 2024/skins/

mkdir -p "/path/to/FM24/skins/test_uxml"
cp build/ui-tiles_assets_all_modified.bundle "/path/to/FM24/skins/test_uxml/"
```

## What to Test

The modified bundle contains changes to `PlayerAttributesTile` UXML:

1. **Launch FM24**
2. **Navigate to a player screen** that shows attributes
3. **Look for the attributes tile** display
4. **Check for:**
   - Any visual changes
   - UI element ordering
   - Layout differences
   - Error messages in console

## Making Your Own Changes

### 1. Find the UXML You Want to Modify

List all available UXML assets:

```python
from src.core.bundle_manager import BundleManager
from pathlib import Path

bundle = BundleManager(Path("bundles/ui-tiles_assets_all.bundle"))
# Find UXML assets by searching for VisualTreeAsset types
```

Or use the asset catalog:

```bash
PYTHONPATH=/workspaces/fm-skin-builder python scripts/build_css_uxml_catalog.py \
  --bundle-dir bundles \
  --output catalog.json \
  --export-files
```

### 2. Export the UXML

```python
from src.core.bundle_manager import BundleManager
from src.utils.uxml_exporter import UXMLExporter
from pathlib import Path

# Load bundle
bundle = BundleManager(Path("bundles/ui-tiles_assets_all.bundle"))

# Get UXML asset
uxml_data = bundle.get_uxml_asset("PlayerAttributesTile")

# Export to XML
exporter = UXMLExporter()
xml = exporter.export_to_xml(uxml_data, export_mode="MINIMAL")

# Save
with open("my_uxml.uxml", "w") as f:
    f.write(xml)
```

### 3. Edit the XML

Open in any text editor and modify:

```xml
<UXML>
  <VisualElement name="Root">
    <!-- Modify element order by changing m_OrderInDocument -->
    <Label name="FirstLabel" m_OrderInDocument="0" />
    <Label name="SecondLabel" m_OrderInDocument="1" />

    <!-- Change parent-child relationships with m_ParentId -->
    <VisualElement name="Container" m_Id="12345">
      <Label name="Child" m_ParentId="12345" />
    </VisualElement>
  </VisualElement>
</UXML>
```

**What You Can Change:**
- ✅ `m_OrderInDocument` - Element display order
- ✅ `m_ParentId` - Which element is the parent
- ✅ `m_Id` - Element identifier (advanced)
- ✅ `m_RuleIndex` - Style rule index (advanced)

**What's Read-Only (for now):**
- ⚠️ Element types (`<Label>`, `<Button>`, etc.)
- ⚠️ Element names (`name="MyLabel"`)
- ⚠️ CSS classes (`class="header"`)
- ⚠️ Binding paths (data-binding attributes)

### 4. Create Your Skin Structure

```bash
mkdir -p skins/my_custom_skin/uxml
```

Create `skins/my_custom_skin/config.json`:

```json
{
  "schema_version": 2,
  "name": "My Custom Skin",
  "author": "Your Name",
  "version": "1.0.0",
  "description": "Custom UXML modifications",
  "includes": ["bundles/ui-tiles_assets_all.bundle"],
  "uxml_overrides": {
    "PlayerAttributesTile": "uxml/PlayerAttributesTile.uxml"
  }
}
```

Copy your modified UXML:
```bash
cp my_uxml.uxml skins/my_custom_skin/uxml/PlayerAttributesTile.uxml
```

### 5. Build Your Custom Bundle

Edit `build_uxml_test.py` to point to your skin:

```python
uxml_file = Path("skins/my_custom_skin/uxml/PlayerAttributesTile.uxml")
```

Then build:

```bash
python build_uxml_test.py
```

## Batch Building Multiple Bundles

If you want to modify multiple UXML assets across different bundles, create a batch script:

```python
# build_all_uxml.py
from pathlib import Path
from src.core.bundle_manager import BundleManager
from src.utils.uxml_importer import UXMLImporter

bundles_to_build = [
    {
        "source": "bundles/ui-tiles_assets_all.bundle",
        "uxml": "skins/my_skin/uxml/PlayerAttributesTile.uxml",
        "asset": "PlayerAttributesTile",
        "output": "build/ui-tiles_assets_all_modified.bundle"
    },
    {
        "source": "bundles/ui-styles_assets_common.bundle",
        "uxml": "skins/my_skin/uxml/CustomButton.uxml",
        "asset": "CustomButton",
        "output": "build/ui-styles_assets_common_modified.bundle"
    }
]

importer = UXMLImporter()

for config in bundles_to_build:
    print(f"Building {config['output']}...")

    bundle = BundleManager(Path(config['source']))
    uxml_data = importer.parse_uxml_file(config['uxml'])

    if bundle.update_uxml_asset(config['asset'], uxml_data):
        bundle.save(Path(config['output']))
        print(f"✓ Success!")
    else:
        print(f"✗ Failed")
```

## Troubleshooting

### Bundle Doesn't Load in Game

- **Verify file size**: Modified bundle should be similar size to original
- **Check permissions**: Ensure file is readable
- **Check FM logs**: Look in FM's log files for errors

### Changes Don't Appear

- **Clear FM cache**: Delete FM's cache folder
- **Verify bundle name**: Must exactly match original
- **Check element IDs**: Make sure IDs are valid integers

### Build Script Fails

- **Check paths**: Ensure bundle and UXML files exist
- **Validate XML**: Make sure UXML is well-formed
- **Check logs**: Look for validation errors

### Element IDs Don't Match

Element IDs must match between the XML and what's in the bundle. If you export fresh XML from a bundle, the IDs will always match. Only change IDs if you know what you're doing.

## Advanced: Debugging UXML Changes

### View Raw Binary Data

```python
import UnityPy
from pathlib import Path

env = UnityPy.load("build/ui-tiles_assets_all_modified.bundle")

for obj in env.objects:
    if obj.type.name == "MonoBehaviour":
        data = obj.read()
        if hasattr(data, 'm_Name') and data.m_Name == "PlayerAttributesTile":
            print(f"Elements: {len(data.m_VisualElementAssets)}")

            # Show first element
            elem = data.m_VisualElementAssets[0]
            print(f"First element:")
            print(f"  ID: {elem.m_Id}")
            print(f"  Order: {elem.m_OrderInDocument}")
            print(f"  Parent: {elem.m_ParentId}")
            print(f"  Type: {elem.m_Type}")
```

### Compare Original vs Modified

```bash
# Export both to JSON for comparison
python scripts/export_uxml_json.py \
  bundles/ui-tiles_assets_all.bundle \
  PlayerAttributesTile \
  original.json

python scripts/export_uxml_json.py \
  build/ui-tiles_assets_all_modified.bundle \
  PlayerAttributesTile \
  modified.json

# Diff the JSON
diff -u original.json modified.json
```

## Next Steps

1. ✅ Build test bundle
2. ✅ Install in FM24
3. ✅ Test in-game
4. 📝 Document what works
5. 🎨 Create more complex modifications
6. 🚀 Share your findings!

## Known Limitations

**Current Version:**
- Can only modify integer fields (IDs, order, parent)
- Can't change element types or names
- Can't add/remove elements
- String modifications require Unity string table support

**Future Enhancements:**
- Full string field support
- Binding path modifications
- Add/remove elements
- Complete structural changes

## References

- `UXML_IMPORT_STATUS.md` - Technical implementation details
- `UXML_USAGE.md` - API and usage documentation
- `EXPORT_MODES.md` - UXML export format reference
