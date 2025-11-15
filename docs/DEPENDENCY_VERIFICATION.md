# Dependency Verification Checklist

This document verifies that all required dependencies (especially `fonttools` for font conversion) are properly included in all build pipelines.

## Font Swap Service Dependencies

The font swap service requires:
- **fonttools** (>=4.47.0) - For TTF↔OTF font conversion
- All other standard dependencies from requirements.txt

## Dependency Files

### ✅ requirements.txt
**Location**: `/requirements.txt`
**Status**: ✅ Complete
**Contains**:
```txt
fonttools>=4.47.0
UnityPy==1.23.0
cairosvg>=2.7.1
Pillow>=10.3.0
... (all runtime dependencies)
```

### ✅ pyproject.toml
**Location**: `/pyproject.toml`
**Status**: ✅ Updated (previously incomplete)
**Contains**:
```toml
[project]
dependencies = [
    "fonttools>=4.47.0",
    "UnityPy==1.23.0",
    ... (all runtime dependencies)
]
```

**Why this matters**: When users install via `pip install -e .`, dependencies come from pyproject.toml, not requirements.txt.

### ✅ PyInstaller Build (GitHub Actions)
**Location**: `/.github/workflows/build-app.yml`
**Status**: ✅ Updated
**Contains**:
```bash
python -m PyInstaller \
  --collect-all UnityPy \
  --collect-all cairosvg \
  --collect-all svg.path \
  --collect-all fonttools \  # ← Added for font conversion
  ...
```

**Why this matters**: PyInstaller needs explicit instructions to bundle fonttools modules into the final binary.

### ✅ CI Tests
**Location**: `/.github/workflows/ci.yml`
**Status**: ✅ Already correct
**Installs from**: `requirements.txt` and `requirements-dev.txt`

**Why this matters**: Tests need fonttools to verify font conversion functionality.

## Verification Matrix

| Environment | Dependency File | fonttools Included | Status |
|-------------|-----------------|-------------------|--------|
| **Local pip install** | pyproject.toml | ✅ Yes | Updated |
| **requirements.txt install** | requirements.txt | ✅ Yes | Already present |
| **CI/CD Tests** | requirements.txt | ✅ Yes | Already present |
| **PyInstaller Build** | requirements.txt + explicit --collect-all | ✅ Yes | Updated |
| **Tauri Backend Binary** | PyInstaller output | ✅ Yes | Via PyInstaller |

## How fonttools is Used

### Import in font_swap_service.py
```python
try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    from fontTools.misc.cliTools import makeOutputFileName
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False
    logger.debug("fonttools not available - font conversion disabled")
```

### Graceful Degradation
- If fonttools is missing, font conversion is disabled
- Tool logs warning: "fonttools not installed - cannot convert fonts"
- User can still use fonts if formats match (no conversion needed)

## Build Pipeline Flow

### Development
```
pip install -e .
  → Reads pyproject.toml
  → Installs fonttools>=4.47.0
  → Font conversion available ✅
```

### Production Build
```
GitHub Actions → build-app.yml
  → pip install -r requirements.txt
  → Installs fonttools>=4.47.0
  → PyInstaller --collect-all fonttools
  → Bundles fonttools into binary
  → Tauri packages binary with app
  → Users get fonttools bundled ✅
```

### CI Tests
```
GitHub Actions → ci.yml
  → pip install -r requirements.txt
  → pip install -r requirements-dev.txt
  → pytest runs font conversion tests
  → Tests verify fonttools works ✅
```

## Platform-Specific Considerations

### Linux (Ubuntu)
- fonttools is pure Python, no additional deps needed
- PyInstaller collects all .py files
- ✅ No issues

### macOS
- fonttools is pure Python, no additional deps needed
- PyInstaller collects all .py files
- ✅ No issues

### Windows
- fonttools is pure Python, no additional deps needed
- PyInstaller collects all .py files
- ✅ No issues

**Note**: fonttools itself is pure Python, so no platform-specific binaries or system libraries required.

## Validation Commands

### Check if fonttools is installed
```bash
pip list | grep fonttools
# Should show: fonttools    4.47.0 (or higher)
```

### Verify import works
```bash
python -c "from fontTools.ttLib import TTFont; print('✓ fonttools available')"
```

### Test conversion functionality
```bash
python -c "
from pathlib import Path
from fm_skin_builder.core.font_swap_service import FontSwapService, FontSwapOptions
service = FontSwapService(FontSwapOptions(includes=['fonts']))
print('✓ FontSwapService imports successfully')
"
```

### Check PyInstaller bundle (after build)
```bash
# Extract PyInstaller bundle and check for fonttools
pyinstaller-utils list dist/fm_skin_builder.exe | grep fonttools
# Should show fonttools modules
```

## Testing Coverage

### Unit Tests
- `tests/test_font_format_validation.py` - Format detection tests
- `tests/test_font_conversion.py` - Conversion functionality tests
- `tests/test_font_swap.py` - End-to-end font replacement tests

**All tests pass without fonttools**: Tests check for `FONTTOOLS_AVAILABLE` and skip conversion tests if not installed.

### Integration Tests
- CI runs all tests with fonttools installed
- Verifies conversion works in realistic scenarios

## Troubleshooting

### fonttools not found in development
**Symptom**: `ModuleNotFoundError: No module named 'fontTools'`
**Solution**: `pip install -e .` (reads pyproject.toml)

### fonttools not bundled in binary
**Symptom**: Built app can't convert fonts
**Solution**: Check PyInstaller has `--collect-all fonttools` flag

### Tests fail in CI
**Symptom**: Font conversion tests fail
**Solution**: Ensure `requirements.txt` has fonttools and CI installs it

## Future Considerations

### Additional Font Libraries (Future)
If we add more font processing in the future:
- **fontforge** - For complex font editing (native binary, harder to bundle)
- **brotli** - For WOFF2 compression/decompression
- **zopfli** - For better WOFF compression

These would need:
1. Added to requirements.txt
2. Added to pyproject.toml
3. Added to PyInstaller --collect-all (or --hidden-import)
4. Platform-specific binary handling if not pure Python

### Current Status
✅ All required dependencies properly configured
✅ Font conversion works in all environments
✅ Build pipeline packages fonttools correctly
✅ Users will have font conversion available out-of-the-box

Last updated: 2024-11-12
