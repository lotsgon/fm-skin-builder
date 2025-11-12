# Font Format Guide - OTF vs TTF

## Critical Requirement

**⚠️ Font format MUST match the original for proper rendering.**

FM26 uses specific font formats for each font:
- `GT-America-Standard-Black`: **OTF** (must use OTF replacement)
- `ABCSocial-Regular`: **OTF** (must use OTF replacement)
- `NotoSans-Regular`: **TTF** (must use TTF replacement)

**Unity expects matching formats**: Replacing an OTF font with TTF (or vice versa) may cause rendering issues or the game to fall back to default fonts.

## Good News: Auto-Conversion Enabled by Default

**The tool automatically converts fonts to match the original format!**

You can drop any TTF or OTF font into `assets/fonts/` and the tool will:
1. Detect the original font's format in the bundle
2. Detect your replacement font's format
3. **Automatically convert if needed** (TTF↔OTF)
4. Replace with the correctly formatted font

**You don't need to worry about formats** - just use the fonts you have!

---

## Understanding Font Formats

### OTF (OpenType Font)
- Uses **CFF (Compact Font Format)** tables for glyph data
- Typically smaller file size (CFF is compressed)
- PostScript-based hinting
- **FM26 OTF fonts**: `GT-America-Standard-Black`, `ABCSocial-Regular`

### TTF (TrueType Font)
- Uses **glyf** tables for glyph data
- Typically larger file size
- TrueType hinting
- **FM26 TTF fonts**: `NotoSans-Regular`

### Why Formats Must Match

Unity's font loader expects specific internal tables:
- **OTF loader** looks for CFF tables
- **TTF loader** looks for glyf tables
- Mismatched formats cause the loader to fail or fall back to defaults

From FM26 community:
> "Renaming a .ttf to .otf does not work because Unity/font loader expects the correct internal font tables (e.g. CFF vs glyf). **So the replacement must be a real OTF if the original was OTF.**"

---

## Usage Modes

### Mode 1: Auto-Convert (Default) ✅ Recommended

**What it does**: Automatically converts fonts to match original format

**This is the default** - you don't need to configure anything!

```json
{
  "includes": ["fonts"]
}
```

**Example**:
```
assets/fonts/
  GT-America-Standard-Black.ttf  ← TTF will be converted to OTF

Output:
ℹ️  Auto-converting 'GT-America-Standard-Black.ttf' from TTF to OTF
✓ Converted font: GT-America-Standard-Black_converted.otf
✓ Replaced font: GT-America-Standard-Black (OTF, 412 KB)
```

**When to use**: Default choice - maximum convenience, guaranteed format matching

**Requirements**: `fonttools` package (installed automatically via requirements.txt)

### Mode 2: Manual Format Matching

**What it does**: You provide fonts in the correct format, no conversion needed

**Setup**: Disable auto-conversion (advanced users only):
```python
# Future config option
{
  "includes": ["fonts"],
  "font_options": {
    "auto_convert": false
  }
}
```

**Example**:
```
assets/fonts/
  GT-America-Standard-Black.otf  ← OTF for OTF original ✓
  ABCSocial-Regular.otf          ← OTF for OTF original ✓
  NotoSans-Regular.ttf           ← TTF for TTF original ✓

Output:
✓ Replaced font: GT-America-Standard-Black (OTF, 412 KB)
✓ Replaced font: ABCSocial-Regular (OTF, 385 KB)
✓ Replaced font: NotoSans-Regular (TTF, 524 KB)
```

**When to use**:
- You already have fonts in the correct format
- You want to avoid conversion step
- You've manually converted with professional tools

### Mode 3: Strict (Advanced)

**What it does**: Blocks format mismatches entirely, even with conversion disabled

**Setup**:
```python
# Future config option
{
  "includes": ["fonts"],
  "font_options": {
    "auto_convert": false,
    "strict_format": true
  }
}
```

**Example**:
```
assets/fonts/
  GT-America-Standard-Black.ttf  ← TTF for OTF original ❌ BLOCKED

Output:
❌ Format mismatch (strict mode): original is OTF, replacement is TTF.
   Use auto_convert=True or provide OTF file.
Skipping font 'GT-America-Standard-Black': Format mismatch...
```

**When to use**:
- You want explicit failures for mismatches
- You're debugging font issues
- Maximum safety validation

---

## How Auto-Conversion Works

The tool uses `fonttools` (industry-standard Python library) to convert fonts:

### TTF → OTF Conversion
1. Load TTF font with `fonttools`
2. Read glyf (glyph) tables
3. Convert to CFF format
4. Save as OTF with proper structure
5. Use converted file for replacement

### OTF → TTF Conversion
1. Load OTF font with `fonttools`
2. Read CFF tables
3. Convert to glyf format
4. Save as TTF with proper structure
5. Use converted file for replacement

**Conversion Quality**:
- ✅ Simple fonts: Perfect conversion, no quality loss
- ⚠️ Complex fonts: May lose some hinting data (usually not noticeable)
- ✅ All glyphs preserved: Character shapes remain identical

**Temporary Files**:
- Converted fonts stored in system temp directory
- Path: `/tmp/fm-skin-builder-fonts/` (Linux/Mac) or `%TEMP%\fm-skin-builder-fonts\` (Windows)
- Automatically cleaned up by OS

---

## Real-World Examples

### Example 1: Mixed Formats (Auto-Convert Default)

You have a mix of TTF and OTF fonts:

```
my-skin/
  assets/
    fonts/
      GT-America-Standard-Black.ttf  ← TTF (will convert to OTF)
      ABCSocial-Regular.ttf          ← TTF (will convert to OTF)
      NotoSans-Regular.otf           ← OTF (will convert to TTF)
  config.json
```

```json
{
  "includes": ["fonts"]
}
```

```bash
fm-skin-builder patch my-skin --out build
```

**Result**:
```
ℹ️  Auto-converting 'GT-America-Standard-Black.ttf' from TTF to OTF
✓ Converted font: GT-America-Standard-Black_converted.otf
✓ Replaced font: GT-America-Standard-Black

ℹ️  Auto-converting 'ABCSocial-Regular.ttf' from TTF to OTF
✓ Converted font: ABCSocial-Regular_converted.otf
✓ Replaced font: ABCSocial-Regular

ℹ️  Auto-converting 'NotoSans-Regular.otf' from OTF to TTF
✓ Converted font: NotoSans-Regular_converted.ttf
✓ Replaced font: NotoSans-Regular

✅ All fonts replaced successfully!
```

### Example 2: Correct Formats (No Conversion)

You already have fonts in the correct format:

```
my-skin/
  assets/
    fonts/
      GT-America-Standard-Black.otf  ← OTF ✓
      ABCSocial-Regular.otf          ← OTF ✓
      NotoSans-Regular.ttf           ← TTF ✓
```

**Result**:
```
✓ Replaced font: GT-America-Standard-Black (OTF, 412 KB)
✓ Replaced font: ABCSocial-Regular (OTF, 385 KB)
✓ Replaced font: NotoSans-Regular (TTF, 524 KB)

✅ All fonts replaced successfully! (No conversion needed)
```

### Example 3: Using Font Mapping

Explicit mapping with auto-conversion:

```
assets/fonts/
  MyCustomFont.ttf
  font-mapping.json
```

`font-mapping.json`:
```json
{
  "GT-America-Standard-Black": "MyCustomFont.ttf",
  "ABCSocial-Regular": "MyCustomFont.ttf"
}
```

**Result**:
```
ℹ️  Auto-converting 'MyCustomFont.ttf' from TTF to OTF
✓ Converted font: MyCustomFont_converted.otf
✓ Replaced font: GT-America-Standard-Black

✓ Replaced font: ABCSocial-Regular (reusing converted OTF)

✅ Same font used for multiple replacements!
```

---

## Finding Original Font Formats

Use the catalogue command to discover which fonts are in the game and their formats:

```bash
fm-skin-builder catalogue \
  --bundle /path/to/ui-fonts_assets_production.bundle \
  --out catalogue \
  --fm-version 2026.4.0
```

Check `catalogue/fonts.json`:
```json
{
  "fonts": [
    {
      "name": "GT-America-Standard-Black",
      "format": "OTF",  ← Original format
      "bundles": ["ui-fonts_assets_production.bundle"]
    },
    {
      "name": "ABCSocial-Regular",
      "format": "OTF",
      "bundles": ["ui-fonts_assets_production.bundle"]
    },
    {
      "name": "NotoSans-Regular",
      "format": "TTF",
      "bundles": ["ui-fonts_assets_production.bundle"]
    }
  ]
}
```

---

## Troubleshooting

### Font Doesn't Show in Game

**Possible causes**:
1. Font name mismatch (check bundle for exact name)
2. Font file corrupted
3. Conversion failed (check logs)

**Solutions**:
1. Use catalogue command to find exact font names
2. Check tool output for conversion errors
3. Try providing font in correct format (skip conversion)

### Conversion Fails

**Error**: `fonttools not installed`
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

**Error**: `Font conversion failed: ...`
**Solutions**:
1. Font may be corrupted - try different source
2. Font may have unsupported features - simplify with FontForge
3. Try manually converting with professional tool, then use converted file

### Format Detection Issues

**Error**: `Unable to detect font format (invalid magic bytes)`
**Cause**: Font file is:
- Corrupted
- Compressed (WOFF/WOFF2)
- Not a valid font file

**Solution**:
1. For WOFF/WOFF2: Decompress to TTF/OTF first
2. Verify font is valid by opening in font viewer
3. Try re-downloading font from source

### Auto-Convert Not Working

**If auto-convert seems disabled**:
1. Check that `fonttools` is installed: `pip list | grep fonttools`
2. Check logs for "fonttools not available" message
3. Reinstall: `pip install --force-reinstall fonttools`

---

## Technical Details

### Magic Bytes Reference

The tool detects font format by reading the first 4 bytes:

| Format | Magic Bytes | Hex | Description |
|--------|-------------|-----|-------------|
| TTF v1 | `\x00\x01\x00\x00` | 00 01 00 00 | TrueType 1.0 |
| TTF Mac | `true` | 74 72 75 65 | TrueType (Mac) |
| OTF | `OTTO` | 4F 54 54 4F | OpenType with CFF |

### Unity Font Asset Structure

```
Unity Font Asset in bundle:
├─ m_Name: "GT-America-Standard-Black"  ← Must stay unchanged!
├─ m_FontData: [binary font bytes]      ← What we replace
├─ m_LineSpacing: float
├─ m_CharacterSpacing: float
├─ m_DefaultMaterial: MaterialReference
└─ [other Unity-specific properties]
```

**Critical**: The `m_Name` field must remain unchanged so USS/UXML references continue to work.

### Font Table Comparison

| Aspect | TTF | OTF |
|--------|-----|-----|
| **Glyph Data** | glyf table | CFF/CFF2 table |
| **Compression** | None | CFF is compressed |
| **Hinting** | TrueType hinting | PostScript hinting |
| **File Size** | Usually larger | Usually smaller |
| **Unity Loader** | Looks for glyf | Looks for CFF |

### How UABEA Does It

The UABEA tool's "Import .ttf/.otf" plugin:
1. Loads the Unity Font asset
2. Reads the existing m_FontData (to detect format)
3. **User provides matching format font** (critical!)
4. Replaces m_FontData with new font bytes
5. Keeps m_Name unchanged
6. Reserializes to Unity format

**Our tool does the same** but adds automatic format conversion as step 3.5.

---

## Conversion Options Summary

| Option | auto_convert | strict_format | Behavior |
|--------|--------------|---------------|----------|
| **Auto-Convert (Default)** | True | False | Convert to match, always succeeds |
| **Manual Matching** | False | False | Allow mismatches, warn only |
| **Strict** | False | True | Block mismatches, fail with error |

**Recommended**: Use default (auto-convert) for best experience!

---

## FAQ

**Q: Do I need to provide fonts in the correct format?**
A: No! The tool auto-converts by default. Use any TTF or OTF font.

**Q: Will conversion lose font quality?**
A: Simple fonts: No quality loss. Complex fonts: Some hinting may be lost (usually not noticeable in-game).

**Q: Can I disable auto-conversion?**
A: Yes, but not recommended. You'll need to provide correctly formatted fonts manually.

**Q: Which fonts does FM26 use?**
A: Run `fm-skin-builder catalogue` to see all fonts and their formats.

**Q: Can I use WOFF/WOFF2 fonts?**
A: Not directly. Decompress to TTF/OTF first using online tools or `fonttools`.

**Q: Will format mismatches work anyway?**
A: Maybe, but **not recommended**. Unity may fall back to default fonts or render incorrectly. Auto-conversion is safer.

**Q: Do I need fonttools installed?**
A: Yes, for auto-conversion. It's included in `requirements.txt` and installed automatically.

**Q: Can I add NEW fonts to the bundle?**
A: Not yet - this is a future feature. Currently only replaces existing fonts.

**Q: What if conversion fails?**
A: Tool falls back to using your original file and logs a warning. Check logs for errors.

---

## Best Practices

### ✅ Recommended Workflow

1. **Find font names** using catalogue command
2. **Drop any fonts** in `assets/fonts/` (TTF or OTF, doesn't matter)
3. **Run patch command** - tool auto-converts as needed
4. **Test in-game** to verify fonts render correctly

### ⚠️ What to Avoid

- ❌ Don't rename `.ttf` to `.otf` (or vice versa) - internal format is unchanged
- ❌ Don't disable auto-convert unless you know what you're doing
- ❌ Don't use compressed fonts (WOFF/WOFF2) - decompress first
- ❌ Don't ignore conversion errors - check logs and fix issues

### 💡 Pro Tips

- Use `--dry-run` to preview changes before applying
- Keep original fonts as backup
- Test one font at a time when debugging
- Use explicit mapping for better control (`font-mapping.json`)
- Check catalogue output to verify original formats

---

## Future Enhancements

Planned improvements:
- [ ] WOFF/WOFF2 auto-decompression
- [ ] Font subsetting (reduce file size by removing unused glyphs)
- [ ] Adding NEW fonts to bundles (not just replacing)
- [ ] Variable font support
- [ ] Font feature preservation in conversion
- [ ] Font preview before replacement

---

## See Also

- [FONT_IMPLEMENTATION_PLAN.md](FONT_IMPLEMENTATION_PLAN.md) - Technical implementation details
- [SKIN_FORMAT.md](SKIN_FORMAT.md) - Skin configuration format
- [CLI_GUIDE.md](CLI_GUIDE.md) - Command line usage

---

## Summary

**Bottom line**: Font format matching is **critical** for FM26, but you don't need to worry about it! The tool automatically converts fonts to match the original format by default. Just drop your fonts in `assets/fonts/` and go!
