# UXML CLI Commands

Complete guide for using UXML export/import via the CLI.

---

## Overview

The UXML functionality is now available as CLI commands:
- `export-uxml` - Export UXML files from Unity bundles
- `import-uxml` - Import UXML files and patch Unity bundles

These commands are designed to be called from your frontend application or used directly from the command line.

---

## Export UXML

### Basic Usage

```bash
python -m fm_skin_builder export-uxml \
  --bundle /path/to/ui.unity3d \
  --out exported_uxml
```

**Result:**
```
exported_uxml/
├── CalendarTool.uxml
├── MatchCalendarDayView.uxml
├── PlayerOverview.uxml
└── ...
```

### Export from Directory

```bash
python -m fm_skin_builder export-uxml \
  --bundle /path/to/bundles/ \
  --out exported_uxml
```

Exports UXML from all `.unity3d` files in the directory.

### Filter Specific Assets

```bash
python -m fm_skin_builder export-uxml \
  --bundle /path/to/ui.unity3d \
  --out exported_uxml \
  --filter "CalendarTool,PlayerOverview,MatchView"
```

Only exports the specified assets (comma-separated).

### Dry Run (Preview)

```bash
python -m fm_skin_builder export-uxml \
  --bundle /path/to/ui.unity3d \
  --out exported_uxml \
  --dry-run
```

Shows what would be exported without writing files.

### All Options

```
--bundle PATH      Bundle file or directory to export from (required)
--out DIR          Output directory for UXML files (default: exported_uxml)
--filter NAMES     Comma-separated list of asset names to export
--dry-run          Preview what would be exported without writing files
```

---

## Import UXML

### Basic Usage

```bash
python -m fm_skin_builder import-uxml \
  --bundle /path/to/ui.unity3d \
  --uxml edited_uxml \
  --out patched_ui.unity3d
```

**Result:** Creates `patched_ui.unity3d` with your UXML changes applied.

### With Backup

```bash
python -m fm_skin_builder import-uxml \
  --bundle /path/to/ui.unity3d \
  --uxml edited_uxml \
  --out patched_ui.unity3d \
  --backup
```

Creates `ui.unity3d.bak` before patching.

### Dry Run (Preview)

```bash
python -m fm_skin_builder import-uxml \
  --bundle /path/to/ui.unity3d \
  --uxml edited_uxml \
  --out patched_ui.unity3d \
  --dry-run
```

Shows what would be imported without modifying the bundle.

### All Options

```
--bundle PATH    Bundle file to patch (required)
--uxml DIR       Directory containing edited UXML files (required)
--out PATH       Output path for patched bundle (required)
--backup         Create .bak backup of original bundle
--dry-run        Preview what would be imported without writing files
```

---

## Complete Workflow

### Step 1: Export All UXML

```bash
python -m fm_skin_builder export-uxml \
  --bundle ~/FM2025/data/ui.unity3d \
  --out ~/my_skin/uxml_source
```

### Step 2: Edit UXML Files

Open files in `~/my_skin/uxml_source/` and edit:

```xml
<!-- CalendarTool.uxml -->
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="container" class="calendar-root">
    <ui:Label name="title" text="My Custom Calendar"
              class="title-text large"
              style="color: #FFD700; font-size: 28px;"/>
  </ui:VisualElement>
</ui:UXML>
```

### Step 3: Import Modified UXML

```bash
python -m fm_skin_builder import-uxml \
  --bundle ~/FM2025/data/ui.unity3d \
  --uxml ~/my_skin/uxml_source \
  --out ~/my_skin/packages/ui.unity3d \
  --backup
```

### Step 4: Install Patched Bundle

Copy `~/my_skin/packages/ui.unity3d` to FM's data folder.

---

## Integration with CSS Patching

Combine UXML and CSS patching in your workflow:

### Method 1: Separate Steps

```bash
# 1. Apply CSS patches
python -m fm_skin_builder patch \
  --css ~/my_skin/css_overrides \
  --bundle ~/FM2025/data/ui.unity3d \
  --out ~/my_skin/packages

# 2. Apply UXML patches to the CSS-patched bundle
python -m fm_skin_builder import-uxml \
  --bundle ~/my_skin/packages/ui.unity3d \
  --uxml ~/my_skin/uxml_edits \
  --out ~/my_skin/packages/ui.unity3d
```

### Method 2: Shell Script

Create `patch_all.sh`:

```bash
#!/bin/bash
SKIN_DIR="$HOME/my_skin"
FM_BUNDLE="$HOME/FM2025/data/ui.unity3d"

# Export UXML (first time only)
# python -m fm_skin_builder export-uxml \
#   --bundle "$FM_BUNDLE" \
#   --out "$SKIN_DIR/uxml_source"

# Patch CSS
python -m fm_skin_builder patch \
  --css "$SKIN_DIR/css_overrides" \
  --bundle "$FM_BUNDLE" \
  --out "$SKIN_DIR/packages"

# Patch UXML
python -m fm_skin_builder import-uxml \
  --bundle "$SKIN_DIR/packages/ui.unity3d" \
  --uxml "$SKIN_DIR/uxml_edits" \
  --out "$SKIN_DIR/packages/ui.unity3d"

echo "✅ Patched bundle: $SKIN_DIR/packages/ui.unity3d"
```

---

## Frontend Integration

### Python Subprocess

```python
import subprocess
from pathlib import Path

def export_uxml(bundle_path: str, output_dir: str, filter_names: list = None):
    """Export UXML files from a bundle"""
    cmd = [
        "python", "-m", "fm_skin_builder", "export-uxml",
        "--bundle", bundle_path,
        "--out", output_dir
    ]

    if filter_names:
        cmd.extend(["--filter", ",".join(filter_names)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Export successful!")
        return True
    else:
        print(f"Export failed: {result.stderr}")
        return False

def import_uxml(bundle_path: str, uxml_dir: str, output_path: str, backup: bool = True):
    """Import UXML files and patch a bundle"""
    cmd = [
        "python", "-m", "fm_skin_builder", "import-uxml",
        "--bundle", bundle_path,
        "--uxml", uxml_dir,
        "--out", output_path
    ]

    if backup:
        cmd.append("--backup")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Import successful!")
        return True
    else:
        print(f"Import failed: {result.stderr}")
        return False

# Usage
export_uxml(
    bundle_path="/Users/lotsg/FM2025/data/ui.unity3d",
    output_dir="/Users/lotsg/my_skin/uxml_source"
)

import_uxml(
    bundle_path="/Users/lotsg/FM2025/data/ui.unity3d",
    uxml_dir="/Users/lotsg/my_skin/uxml_edits",
    output_path="/Users/lotsg/my_skin/packages/ui.unity3d",
    backup=True
)
```

### Node.js / Electron

```javascript
const { exec } = require('child_process');
const path = require('path');

function exportUXML(bundlePath, outputDir, filterNames = null) {
  return new Promise((resolve, reject) => {
    let cmd = `python -m fm_skin_builder export-uxml --bundle "${bundlePath}" --out "${outputDir}"`;

    if (filterNames && filterNames.length > 0) {
      cmd += ` --filter "${filterNames.join(',')}"`;
    }

    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        reject(stderr);
      } else {
        resolve(stdout);
      }
    });
  });
}

function importUXML(bundlePath, uxmlDir, outputPath, backup = true) {
  return new Promise((resolve, reject) => {
    let cmd = `python -m fm_skin_builder import-uxml --bundle "${bundlePath}" --uxml "${uxmlDir}" --out "${outputPath}"`;

    if (backup) {
      cmd += ' --backup';
    }

    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        reject(stderr);
      } else {
        resolve(stdout);
      }
    });
  });
}

// Usage
exportUXML(
  '/Users/lotsg/FM2025/data/ui.unity3d',
  '/Users/lotsg/my_skin/uxml_source'
).then(console.log).catch(console.error);

importUXML(
  '/Users/lotsg/FM2025/data/ui.unity3d',
  '/Users/lotsg/my_skin/uxml_edits',
  '/Users/lotsg/my_skin/packages/ui.unity3d',
  true
).then(console.log).catch(console.error);
```

---

## Advantages of CLI Commands

### 1. No Import Errors
The CLI commands are part of the installed package, so no `ModuleNotFoundError` issues.

### 2. Frontend Ready
Easy to call from any frontend:
- Python subprocess
- Node.js exec
- Electron IPC
- Web API endpoints

### 3. Consistent Interface
Same as other commands (`patch`, `scan`, `catalogue`).

### 4. Easy Bundling
When you bundle your frontend app, just include the `fm_skin_builder` package.

### 5. Supports Filtering
Export only specific UXML files for UI editing:
```bash
--filter "CalendarTool,PlayerOverview"
```

---

## Common Workflows

### Workflow 1: Full Skin Development

```bash
# 1. Export all UXML (one-time)
python -m fm_skin_builder export-uxml \
  --bundle ui.unity3d \
  --out my_skin/uxml_source

# 2. Copy files you want to modify
cp my_skin/uxml_source/CalendarTool.uxml my_skin/uxml_edits/

# 3. Edit my_skin/uxml_edits/CalendarTool.uxml

# 4. Patch (CSS + UXML)
python -m fm_skin_builder patch \
  --css my_skin/css_overrides \
  --bundle ui.unity3d \
  --out my_skin/packages

python -m fm_skin_builder import-uxml \
  --bundle my_skin/packages/ui.unity3d \
  --uxml my_skin/uxml_edits \
  --out my_skin/packages/ui.unity3d
```

### Workflow 2: Quick UXML Edit

```bash
# Export single file
python -m fm_skin_builder export-uxml \
  --bundle ui.unity3d \
  --out temp \
  --filter "PlayerOverview"

# Edit temp/PlayerOverview.uxml

# Patch
python -m fm_skin_builder import-uxml \
  --bundle ui.unity3d \
  --uxml temp \
  --out ui_patched.unity3d \
  --backup
```

### Workflow 3: Frontend App Flow

```
User clicks "Export UXML" in your app
  ↓
Frontend calls: export-uxml --bundle ... --out ...
  ↓
Display list of UXML files in UI
  ↓
User selects and edits files in built-in editor
  ↓
User clicks "Apply Changes"
  ↓
Frontend calls: import-uxml --bundle ... --uxml ... --out ...
  ↓
Show success message and offer to install bundle
```

---

## Troubleshooting

### "No VisualTreeAssets found"
- Check bundle path is correct
- UI assets usually in `ui.unity3d` or similar

### "No UXML files were imported"
- Ensure UXML filenames match VTA asset names exactly
- Check UXML directory path is correct

### "Failed to export/import"
- Check logs for specific errors
- Verify UXML syntax (must be valid XML)
- Ensure you have write permissions

---

## Summary

**Export:**
```bash
python -m fm_skin_builder export-uxml --bundle BUNDLE --out DIR [--filter NAMES] [--dry-run]
```

**Import:**
```bash
python -m fm_skin_builder import-uxml --bundle BUNDLE --uxml DIR --out OUTPUT [--backup] [--dry-run]
```

**Perfect for:**
- ✅ Frontend integration
- ✅ Automation scripts
- ✅ CI/CD pipelines
- ✅ Batch processing
- ✅ No import errors

See **UXML_MANIPULATION_GUIDE.md** for UXML editing syntax and examples.
