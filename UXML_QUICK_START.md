# UXML Export/Import Quick Start Guide

Step-by-step guide to export, edit, and reimport UXML files.

---

## Overview

The UXML pipeline lets you:
1. **Export** VTA assets to human-readable UXML files
2. **Edit** the UXML in any text editor
3. **Reimport** the modified UXML back to VTA format
4. **Patch** bundles with your changes

---

## Method 1: Python Scripts (Recommended for Testing)

### Step 1: Export UXML from a Bundle

Create `export_uxml.py`:

```python
#!/usr/bin/env python3
"""Export UXML files from a bundle"""
from pathlib import Path
from fm_skin_builder.core.unity.asset_bundle import AssetBundle
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter

# Configuration
BUNDLE_PATH = Path("path/to/your/bundle.unity3d")  # Your FM bundle
OUTPUT_DIR = Path("exported_uxml")  # Where to save UXML files

def export_all_uxml():
    """Export all VisualTreeAssets from a bundle as UXML files"""
    print(f"Loading bundle: {BUNDLE_PATH}")
    bundle = AssetBundle.from_file(BUNDLE_PATH)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

    # Find all VisualTreeAssets
    vta_count = 0
    exporter = UXMLExporter()

    for obj in bundle.objects:
        if obj.type.name == "MonoBehaviour":
            # Check if it's a VisualTreeAsset
            data = obj.read()
            type_name = getattr(data, "m_ClassName", None)

            if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                vta_count += 1

                # Generate filename from object name or ID
                asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                if not asset_name:
                    asset_name = f"VTA_{obj.path_id}"

                # Export to UXML
                output_file = OUTPUT_DIR / f"{asset_name}.uxml"
                print(f"  Exporting: {asset_name} -> {output_file}")

                doc = exporter.export_visual_tree_asset(data, asset_name=asset_name)
                exporter.write_uxml(doc, output_file)

    print(f"\n✅ Exported {vta_count} UXML files to {OUTPUT_DIR}")

if __name__ == "__main__":
    export_all_uxml()
```

**Run it:**
```bash
python export_uxml.py
```

**Output:**
```
exported_uxml/
├── CalendarTool.uxml
├── MatchCalendarDayView.uxml
├── PlayerOverview.uxml
└── ... (all your UI files)
```

---

### Step 2: Edit the UXML Files

Open any UXML file in a text editor:

```xml
<!-- exported_uxml/CalendarTool.uxml -->
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="container" class="calendar-root">
    <ui:Label name="title" text="Calendar"
              class="title-text large"
              style="color: #FFFFFF;"/>

    <ui:Button name="next-btn" text="Next Week"
               class="nav-button primary"/>
  </ui:VisualElement>
</ui:UXML>
```

**Make your changes:**
```xml
<!-- Example: Change title color and add a new button -->
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="container" class="calendar-root dark-theme">
    <ui:Label name="title" text="My Custom Calendar"
              class="title-text large bold"
              style="color: #FFD700; font-size: 28px;"/>

    <ui:Button name="next-btn" text="Next Week"
               class="nav-button primary"/>

    <!-- NEW: Add a custom button -->
    <ui:Button name="custom-btn" text="Custom Action"
               class="nav-button secondary"
               style="background-color: #FF5722;"/>
  </ui:VisualElement>
</ui:UXML>
```

---

### Step 3: Reimport UXML to VTA

Create `import_uxml.py`:

```python
#!/usr/bin/env python3
"""Import UXML files and update a bundle"""
from pathlib import Path
from fm_skin_builder.core.unity.asset_bundle import AssetBundle
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter

# Configuration
BUNDLE_PATH = Path("path/to/your/bundle.unity3d")  # Original bundle
OUTPUT_BUNDLE = Path("path/to/modified_bundle.unity3d")  # Modified bundle
UXML_DIR = Path("exported_uxml")  # Your edited UXML files

def import_uxml_to_bundle():
    """Import edited UXML files back into a bundle"""
    print(f"Loading bundle: {BUNDLE_PATH}")
    bundle = AssetBundle.from_file(BUNDLE_PATH)

    importer = UXMLImporter()
    modified_count = 0

    # Find all VisualTreeAssets and update them
    for obj in bundle.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.read()
            type_name = getattr(data, "m_ClassName", None)

            if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                if not asset_name:
                    asset_name = f"VTA_{obj.path_id}"

                # Check if we have a modified UXML for this asset
                uxml_file = UXML_DIR / f"{asset_name}.uxml"

                if uxml_file.exists():
                    print(f"  Importing: {asset_name} from {uxml_file}")

                    # Import UXML
                    doc = importer.import_uxml(uxml_file)

                    # Convert back to VTA structure
                    vta_structure = importer.build_visual_tree_asset(doc)

                    # Update the object's data
                    # NOTE: This updates the in-memory data structure
                    for key, value in vta_structure.items():
                        setattr(data, key, value)

                    # Write updated data back to object
                    obj.save_typetree(data)

                    modified_count += 1

    # Save modified bundle
    print(f"\nSaving modified bundle to: {OUTPUT_BUNDLE}")
    bundle.save(OUTPUT_BUNDLE)

    print(f"\n✅ Modified {modified_count} VTA assets")
    print(f"✅ Bundle saved: {OUTPUT_BUNDLE}")

if __name__ == "__main__":
    import_uxml_to_bundle()
```

**Run it:**
```bash
python import_uxml.py
```

---

### Step 4: Test the Modified Bundle

Replace the original bundle with your modified one in FM's data folder, or use your patch tool to install it.

---

## Method 2: Integration with Patch Tool

You can add UXML support to your existing patch workflow.

### Create a Patch Command Extension

Create `patch_with_uxml.py`:

```python
#!/usr/bin/env python3
"""Patch bundles with CSS + UXML modifications"""
from pathlib import Path
from fm_skin_builder.core.css_patcher import run_patch
from fm_skin_builder.core.unity.asset_bundle import AssetBundle
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter

def patch_with_uxml(
    css_dir: Path,
    uxml_dir: Path,
    bundle_path: Path,
    out_dir: Path
):
    """
    Patch a bundle with both CSS and UXML modifications

    Args:
        css_dir: Directory containing .css/.uss overrides
        uxml_dir: Directory containing .uxml overrides
        bundle_path: Bundle file to patch
        out_dir: Output directory for patched bundle
    """
    # Step 1: Apply CSS patches (your existing workflow)
    print("Step 1: Applying CSS patches...")
    result = run_patch(
        css_dir=css_dir,
        out_dir=out_dir,
        bundle=bundle_path,
        patch_direct=True,
        debug_export=False,
        backup=True,
        dry_run=False,
        use_scan_cache=True,
        refresh_scan_cache=False,
    )

    # Step 2: Apply UXML patches
    print("\nStep 2: Applying UXML patches...")
    patched_bundle = out_dir / bundle_path.name

    bundle = AssetBundle.from_file(patched_bundle)
    importer = UXMLImporter()
    modified_count = 0

    # Find and update VTAs
    for obj in bundle.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.read()
            type_name = getattr(data, "m_ClassName", None)

            if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                asset_name = getattr(data, "m_Name", "")
                uxml_file = uxml_dir / f"{asset_name}.uxml"

                if uxml_file.exists():
                    print(f"  Patching VTA: {asset_name}")
                    doc = importer.import_uxml(uxml_file)
                    vta_structure = importer.build_visual_tree_asset(doc)

                    for key, value in vta_structure.items():
                        setattr(data, key, value)

                    obj.save_typetree(data)
                    modified_count += 1

    bundle.save(patched_bundle)

    print(f"\n✅ CSS patches applied: {result.css_bundles_modified} bundles")
    print(f"✅ UXML patches applied: {modified_count} assets")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Patch bundles with CSS + UXML")
    parser.add_argument("--css", required=True, help="CSS override directory")
    parser.add_argument("--uxml", required=True, help="UXML override directory")
    parser.add_argument("--bundle", required=True, help="Bundle to patch")
    parser.add_argument("--out", required=True, help="Output directory")

    args = parser.parse_args()

    patch_with_uxml(
        css_dir=Path(args.css),
        uxml_dir=Path(args.uxml),
        bundle_path=Path(args.bundle),
        out_dir=Path(args.out)
    )
```

**Usage:**
```bash
python patch_with_uxml.py \
  --css my_skin/css_overrides \
  --uxml my_skin/uxml_overrides \
  --bundle "FM/data/ui.unity3d" \
  --out my_skin/packages
```

---

## Typical Workflow

### Project Structure
```
my_skin/
├── css_overrides/          # USS file overrides
│   ├── BaseStyles.uss
│   └── Themes.uss
├── uxml_overrides/         # UXML file overrides
│   ├── CalendarTool.uxml
│   └── PlayerOverview.uxml
├── packages/               # Output (patched bundles)
└── skin.fmf               # Skin manifest
```

### Steps

1. **Export UXML** (one-time setup):
   ```bash
   python export_uxml.py
   # Creates exported_uxml/ with all UXML files
   ```

2. **Edit what you need**:
   - Edit USS files in `css_overrides/`
   - Edit UXML files in `uxml_overrides/`

3. **Patch the bundle**:
   ```bash
   python patch_with_uxml.py \
     --css my_skin/css_overrides \
     --uxml my_skin/uxml_overrides \
     --bundle "FM/data/ui.unity3d" \
     --out my_skin/packages
   ```

4. **Test in FM**:
   - Copy `my_skin/packages/ui.unity3d` to FM's data folder
   - Launch FM and check your changes

---

## Quick Reference: Common Edits

### Change Text
```xml
<!-- Before -->
<ui:Label text="Original Text"/>

<!-- After -->
<ui:Label text="My Custom Text"/>
```

### Change Classes
```xml
<!-- Before -->
<ui:Button class="primary-button"/>

<!-- After -->
<ui:Button class="primary-button large animated"/>
```

### Add Inline Styles
```xml
<!-- Before -->
<ui:Label class="title-text"/>

<!-- After -->
<ui:Label class="title-text" style="color: #FFD700; font-size: 24px;"/>
```

### Add a New Element
```xml
<ui:VisualElement name="container">
  <ui:Label text="Existing"/>

  <!-- NEW: Add a button -->
  <ui:Button name="my-btn" text="Click Me" class="custom-button"/>
</ui:VisualElement>
```

### Remove an Element
```xml
<!-- Just delete the line -->
<ui:VisualElement name="container">
  <ui:Label text="Keep this"/>
  <!-- DELETED: <ui:Button name="remove-me"/> -->
</ui:VisualElement>
```

---

## Testing Tips

### 1. Start Small
Export and modify just ONE UXML file first to verify your workflow.

### 2. Verify Round-Trip
Export → Import → Export again and compare:
```bash
python export_uxml.py  # Creates exported_uxml/
python import_uxml.py   # Creates modified bundle
# Test the bundle in FM
```

### 3. Use Debug Export
Add `--debug-export` to see before/after comparisons:
```bash
python patch_with_uxml.py --debug-export ...
```

### 4. Keep Backups
Always backup your original bundles before patching!

---

## Troubleshooting

### "No VTAs found"
- Make sure you're pointing to the right bundle
- UI assets are usually in `ui.unity3d` or similar

### "Import failed"
- Check UXML syntax (must be valid XML)
- Ensure namespace is correct: `xmlns:ui="UnityEngine.UIElements"`
- Validate element types match Unity's UIElements

### "Changes not visible in FM"
- Verify the modified bundle is in the right location
- Clear FM's cache
- Check FM logs for errors

---

## Next Steps

1. Try the export script on your FM bundle
2. Edit one UXML file
3. Reimport and test
4. Integrate into your skin workflow

See **UXML_MANIPULATION_GUIDE.md** for complete API documentation and advanced examples.
