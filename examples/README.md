# UXML Export/Import Examples

Ready-to-use scripts for exporting and importing UXML files.

---

## ⭐ Recommended: Use CLI Commands

**The easiest way to use UXML export/import is via the CLI:**

```bash
# Export
python -m fm_skin_builder export-uxml --bundle ui.unity3d --out exported_uxml

# Import
python -m fm_skin_builder import-uxml --bundle ui.unity3d --uxml edited_uxml --out patched.unity3d
```

**See [CLI_UXML_USAGE.md](../CLI_UXML_USAGE.md) for complete CLI documentation.**

---

## Alternative: Standalone Scripts

If you prefer standalone scripts, you can use these examples:

### 1. Export UXML from a Bundle

```bash
python export_uxml.py --bundle /path/to/ui.unity3d --out exported_uxml
```

This creates `exported_uxml/` with all UXML files:
```
exported_uxml/
├── CalendarTool.uxml
├── MatchCalendarDayView.uxml
├── PlayerOverview.uxml
└── ...
```

### 2. Edit UXML Files

Open any `.uxml` file in a text editor and make changes:

```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <ui:VisualElement name="container" class="main-panel">
    <ui:Label name="title" text="My Custom Title"
              class="title-text large"
              style="color: #FFD700;"/>
  </ui:VisualElement>
</ui:UXML>
```

### 3. Import UXML back to Bundle

```bash
python import_uxml.py \
  --bundle /path/to/ui.unity3d \
  --uxml exported_uxml \
  --out patched_ui.unity3d
```

This creates `patched_ui.unity3d` with your changes applied.

---

## Examples

### Example 1: Simple Text Change

**Export:**
```bash
python export_uxml.py --bundle ui.unity3d --out my_edits
```

**Edit** `my_edits/CalendarTool.uxml`:
```xml
<!-- Change -->
<ui:Label text="Calendar"/>

<!-- To -->
<ui:Label text="My Custom Calendar"/>
```

**Import:**
```bash
python import_uxml.py --bundle ui.unity3d --uxml my_edits --out ui_patched.unity3d
```

---

### Example 2: Add Custom Button

**Edit** `my_edits/PlayerOverview.uxml`:
```xml
<ui:VisualElement name="actions">
  <ui:Button text="View Stats" class="action-button"/>

  <!-- ADD NEW BUTTON -->
  <ui:Button text="Custom Action" class="action-button highlight"
             style="background-color: #FF5722;"/>
</ui:VisualElement>
```

**Import:**
```bash
python import_uxml.py --bundle ui.unity3d --uxml my_edits --out ui_patched.unity3d
```

---

### Example 3: Restyle with Inline CSS

**Edit** multiple files in `my_edits/`:
```xml
<!-- Add inline styles to override USS -->
<ui:Label class="title-text" style="color: #FFD700; font-size: 28px;"/>
<ui:Button class="primary" style="background-color: #007ACC;"/>
```

**Import all at once:**
```bash
python import_uxml.py --bundle ui.unity3d --uxml my_edits --out ui_patched.unity3d
```

---

## Command Reference

### export_uxml.py

**Required:**
- `--bundle PATH` - Unity bundle file to export from

**Optional:**
- `--out DIR` - Output directory (default: `exported_uxml`)

**Example:**
```bash
python export_uxml.py \
  --bundle "C:/Program Files/Steam/steamapps/common/FM2025/data/ui.unity3d" \
  --out my_skin/uxml_source
```

---

### import_uxml.py

**Required:**
- `--bundle PATH` - Original Unity bundle file
- `--uxml DIR` - Directory with edited UXML files
- `--out PATH` - Output path for patched bundle

**Optional:**
- `--no-backup` - Skip creating `.bak` backup

**Example:**
```bash
python import_uxml.py \
  --bundle ui.unity3d \
  --uxml my_skin/uxml_edits \
  --out my_skin/packages/ui.unity3d
```

---

## Workflow Tips

### Organize Your Files

```
my_skin/
├── uxml_source/       # Original exported UXML (reference)
├── uxml_edits/        # Your edited versions
├── packages/          # Patched bundles (output)
└── README.md
```

### Selective Patching

You don't need to provide ALL UXML files. Only include the ones you've edited:

```
uxml_edits/
├── CalendarTool.uxml       # Modified
└── PlayerOverview.uxml     # Modified
# (other files will remain unchanged in bundle)
```

### Version Control

Track your UXML edits with git:

```bash
cd my_skin/uxml_edits
git init
git add *.uxml
git commit -m "Initial UXML customizations"
```

---

## Integration with CSS Patcher

Combine UXML and CSS/USS patching:

### Step 1: Patch CSS (existing workflow)
```bash
python -m fm_skin_builder patch \
  --css my_skin/css_overrides \
  --bundle ui.unity3d \
  --out my_skin/packages
```

### Step 2: Patch UXML (new workflow)
```bash
python import_uxml.py \
  --bundle my_skin/packages/ui.unity3d \
  --uxml my_skin/uxml_edits \
  --out my_skin/packages/ui.unity3d
```

Now `my_skin/packages/ui.unity3d` has both CSS and UXML patches!

---

## Troubleshooting

**"No VisualTreeAssets found"**
- Wrong bundle file (try `ui.unity3d` or similar)
- Bundle is corrupted

**"Failed to export"**
- Some VTAs might have unsupported features
- Check logs for specific errors

**"Failed to import"**
- UXML syntax error (must be valid XML)
- Wrong element types
- Missing namespace

**"Changes not visible in FM"**
- Make sure patched bundle is in correct location
- Clear FM cache
- Restart FM

---

## Next Steps

- See **UXML_QUICK_START.md** for full tutorial
- See **UXML_MANIPULATION_GUIDE.md** for API docs
- Check **STYLE_AND_MANIPULATION_COMPLETE.md** for feature overview
