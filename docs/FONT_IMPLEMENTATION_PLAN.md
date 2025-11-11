# Font Replacement Implementation Plan

## Decision Summary

**Recommendation: Implement Font Replacement First**

Decision made: 2025-11-11

### Key Rationale
1. Leverage existing font extraction infrastructure and Python scripts
2. Faster time to value (2-3 weeks vs 4-6 weeks for Advanced CSS)
3. Lower implementation risk (file replacement vs complex CSS parsing)
4. Higher user impact (font changes are immediately visible)
5. Clear success criteria and proven pattern (TextureSwapService)

---

## Current State

### Working Components
- ✅ **FontExtractor**: Extracts font metadata from bundles
- ✅ **Font Model**: Basic data model with name, bundles, tags
- ✅ **Replacement Stub**: `bundle_manager.py:43-51` has basic font replacement logic
- ✅ **Catalogue Export**: Fonts exported to `fonts.json`

### Gaps
- ❌ No FontSwapService (service layer)
- ❌ No font discovery system (no `assets/fonts/` convention)
- ❌ No CLI integration (`--include fonts` flag)
- ❌ No font validation (format checking)
- ❌ No test coverage for font replacement

---

## Implementation Phases

### Phase 1: Core Font Replacement Service (Week 1)
**Estimated effort: 20-25 hours**

#### 1.1 Create FontSwapService
**File**: `fm_skin_builder/services/font_swap_service.py`

Pattern from TextureSwapService:
```python
class FontSwapService:
    def __init__(self, skin_dir: Path):
        self.font_dir = skin_dir / "assets" / "fonts"
        self.font_mapping = self._discover_fonts()

    def _discover_fonts(self) -> Dict[str, Path]:
        """Discover fonts in assets/fonts/ directory."""
        # FontName.ttf → replaces "FontName" in bundles
        # FontName.otf → replaces "FontName" in bundles

    def apply(self, bundle_ctx: BundleContext, report: PatchReport) -> None:
        """Apply font replacements to bundle."""
        for font_name, font_file in self.font_mapping.items():
            if bundle_ctx.manager.replace_asset(font_name, font_file):
                report.fonts_replaced += 1
                logger.info(f"Replaced font: {font_name}")
```

#### 1.2 Font Discovery Conventions

**Primary**: Stem-based matching (like textures)
```
assets/fonts/DINPro-Medium.ttf → replaces "DINPro-Medium"
assets/fonts/Roboto-Regular.otf → replaces "Roboto-Regular"
```

**Alternative**: Explicit mapping file
```json
// assets/fonts/font-mapping.json
{
  "DINPro-Medium": "CustomFont.ttf",
  "Roboto-Regular": "MyRoboto.ttf",
  "DINPro-Bold": "fonts/bold/CustomBold.ttf"
}
```

#### 1.3 Font File Validation (Basic)
- Check file exists and is readable
- Check extension (.ttf, .otf)
- Warn if file size > 5MB
- More advanced validation in Phase 2

#### 1.4 Enhance BundleManager
**File**: `fm_skin_builder/core/bundle_manager.py`

Current stub (lines 43-51):
```python
if obj.type.name == "Font":
    data = obj.read()
    if getattr(data, "m_Name", None) == internal_path:
        font_bytes = new_file.read_bytes()
        data.m_FontData = font_bytes
        obj.save_typetree(data)
        logger.info(f"Replaced font data for {internal_path}")
        replaced = True
        self.modified = True
```

Enhancements needed:
- Better error handling
- Validate font bytes before assignment
- Track which fonts were replaced
- Support dry-run mode

#### 1.5 Integration with Patch Pipeline
**File**: `fm_skin_builder/main.py`

Add to `main_patch_pipeline()`:
```python
# After CSS patching, before saving
if "fonts" in includes or "all" in includes:
    font_service = FontSwapService(skin_dir)
    for bundle_name, bundle_ctx in bundle_contexts.items():
        font_service.apply(bundle_ctx, report)
```

#### 1.6 Update PatchReport
**File**: `fm_skin_builder/models.py`

Add field:
```python
@dataclass
class PatchReport:
    # ... existing fields ...
    fonts_replaced: int = 0
```

Update display in CLI to show fonts replaced.

#### 1.7 CLI Support
**File**: `fm_skin_builder/cli.py`

- `--include fonts` flag (already exists for textures)
- Ensure "fonts" is recognized as valid include value
- Update help text to mention font replacement

#### Deliverables
- ✅ FontSwapService working
- ✅ Font discovery from `assets/fonts/`
- ✅ Integration with patch command
- ✅ CLI support (`--include fonts`)
- ✅ Basic validation
- ✅ Reporting (fonts replaced count)

---

### Phase 2: Font Validation & Error Handling (Week 2)
**Estimated effort: 15-20 hours**

#### 2.1 Font File Validation
**File**: `fm_skin_builder/core/validators/font_validator.py` (new)

Validation checks:
1. **Format Detection**: Check magic bytes
   - TTF: `\x00\x01\x00\x00` or `true` (0x74727565)
   - OTF: `OTTO`
   - WOFF: `wOFF` (future support)
   - WOFF2: `wOF2` (future support)

2. **Size Validation**:
   - Warn if > 5MB
   - Error if > 50MB (Unity bundle limits)

3. **Basic Header Parsing** (if possible):
   - Try to read font name from name table
   - Validate file isn't corrupted

4. **Format Compatibility**:
   - Warn if replacing TTF with OTF or vice versa
   - Check if Unity supports the format

```python
class FontValidator:
    SUPPORTED_FORMATS = {'.ttf', '.otf'}
    MAX_SIZE_MB = 50
    WARN_SIZE_MB = 5

    def validate(self, font_path: Path) -> ValidationResult:
        """Validate font file."""
        # Check existence, format, size, magic bytes
        # Return ValidationResult with errors/warnings
```

#### 2.2 Enhanced Font Metadata Extraction
**File**: `fm_skin_builder/core/catalogue/extractors/font_extractor.py`

Extend Font model to capture:
```python
@dataclass
class Font(BaseModel):
    name: str
    bundles: List[str]
    tags: List[str]
    # NEW FIELDS:
    family: Optional[str] = None      # Font family name
    style: Optional[str] = None       # Regular, Bold, Italic, etc.
    weight: Optional[int] = None      # 100-900
    format: Optional[str] = None      # TTF, OTF
    file_size: Optional[int] = None   # Size in bytes
    status: AssetStatus
    first_seen: str
    last_seen: str
```

Extract metadata from Unity Font object:
- Check if UnityPy exposes font properties
- Parse from m_FontData if needed
- Fallback to name-based heuristics

#### 2.3 Error Handling & Reporting

**Scenarios to handle**:
1. Font file not found
2. Invalid font format
3. Corrupted font file
4. Font name mismatch (replacement target not in bundle)
5. Multiple fonts with same name

**User-friendly messages**:
```
❌ Font replacement failed: DINPro-Medium
   Reason: Font file not found at assets/fonts/DINPro-Medium.ttf

⚠️  Font size warning: CustomFont.ttf (8.2 MB)
   Consider optimizing font file size

✅ Replaced font: DINPro-Medium (256 KB → 412 KB)
```

#### 2.4 Dry-Run Support

Show what would be replaced without modifying:
```
fm-skin-builder patch --include fonts --dry-run

Would replace fonts:
  - DINPro-Medium (fonts_assets) ← assets/fonts/DINPro-Medium.ttf
  - Roboto-Regular (fonts_assets) ← assets/fonts/Roboto.ttf

Total: 2 fonts would be replaced
```

#### 2.5 Debug Export

Add to debug export directory:
```
debug/
  fonts/
    original/
      DINPro-Medium-metadata.json
    replacements/
      DINPro-Medium-replacement.json
```

Metadata includes:
- Original font name, size, format
- Replacement font name, size, format
- Bundle location
- Success/failure status

#### 2.6 Testing
**File**: `tests/test_font_swap_service.py` (new)

Test coverage:
- Font discovery (stem matching, mapping file)
- Font validation (valid/invalid formats)
- Font replacement (mock UnityPy objects)
- Error handling (missing files, invalid formats)
- Dry-run mode
- Reporting

**File**: `tests/test_font_validator.py` (new)

Test coverage:
- Magic byte detection
- Size validation
- Format compatibility checks
- Error message formatting

#### Deliverables
- ✅ Comprehensive font validation
- ✅ Enhanced font metadata extraction
- ✅ Robust error handling
- ✅ Dry-run support
- ✅ Debug export for fonts
- ✅ Test coverage (>80%)
- ✅ Documentation updates

---

### Phase 3: CSS Font Properties (Week 3 - Optional)
**Estimated effort: 20-25 hours**

This phase bridges font replacement with advanced CSS capabilities.

#### 3.1 Extend CSS Patcher for Font Properties

**Properties to support**:
1. `font-family` (Type 3: String or Type 7: Resource)
2. `font-size` (Type 2: Float with unit)
3. `font-weight` (Type 2: Float - 100, 400, 700, etc.)
4. `-unity-font-style` (Type 1: Enum - normal, bold, italic, bold-italic)
5. `-unity-text-align` (Type 1: Enum - upper-left, upper-center, etc.)

#### 3.2 Value Type Handlers

**File**: `fm_skin_builder/services/css/value_parsers.py` (new)

```python
class FontPropertyHandler:
    def parse_font_family(self, value: str) -> Any:
        """Parse font-family value."""
        # "CustomFont" → Unity Font asset reference
        # Handle quoted strings: "Custom Font", 'Custom Font'
        # Handle fallback chains: "CustomFont", "DINPro-Medium"

    def parse_font_size(self, value: str) -> tuple[float, Unit]:
        """Parse font-size value."""
        # "14px" → (14.0, Unit.PIXEL)
        # "1.2em" → (1.2, Unit.EM)
        # "120%" → (1.2, Unit.PERCENT)

    def parse_font_weight(self, value: str) -> int:
        """Parse font-weight value."""
        # "bold" → 700
        # "normal" → 400
        # "100" → 100
```

#### 3.3 Integration with CssPatcher

**File**: `fm_skin_builder/services/css/css_patcher.py`

Extend `_patch_property_value()` to handle font properties:
```python
def _patch_property_value(self, prop, new_value, debug_info):
    value_type = prop.values[0]  # Type: ValueType

    if value_type == 4:  # Color
        # Existing color patching logic
        ...
    elif value_type == 2:  # Float (font-size, font-weight)
        self._patch_float_value(prop, new_value, debug_info)
    elif value_type == 3:  # String (font-family)
        self._patch_string_value(prop, new_value, debug_info)
    elif value_type == 1:  # Enum (font-style, text-align)
        self._patch_enum_value(prop, new_value, debug_info)
```

#### 3.4 Font Family Mapping

**File**: `assets/fonts/font-mapping.json` (enhanced)

Extended mapping to include CSS font-family names:
```json
{
  "replacements": {
    "DINPro-Medium": "CustomFont.ttf",
    "Roboto-Regular": "Roboto.ttf"
  },
  "css_mappings": {
    "CustomFont": "DINPro-Medium",
    "MyRoboto": "Roboto-Regular"
  }
}
```

CSS usage:
```css
.header {
  font-family: "CustomFont";  /* Maps to DINPro-Medium asset */
  font-size: 18px;
  font-weight: 700;
}
```

#### 3.5 Testing

**File**: `tests/test_css_font_properties.py` (new)

Test coverage:
- Font-family patching
- Font-size patching (various units)
- Font-weight patching
- Font-style patching
- Integration with font replacement

#### 3.6 Documentation

**File**: `docs/recipes/font-replacement.md` (new)

Recipe covering:
- Basic font replacement
- CSS font property overrides
- Font mapping configuration
- Troubleshooting common issues

#### Deliverables
- ✅ CSS font property support
- ✅ Font family mapping system
- ✅ Integration with existing CSS patcher
- ✅ Test coverage
- ✅ Documentation and examples

---

## Alternative: Advanced CSS Implementation

If we decide to pursue Advanced CSS instead, here's the high-level plan:

### Phase 1: Value Type Expansion (Week 1-2)
- Add Float (Type 2) handling
- Add Boolean (Type 1) handling
- Add Resource Reference (Type 7) handling
- Multi-value property parsing

### Phase 2: Property Categories (Week 3-4)
- Font properties (font-size, font-weight, etc.)
- Dimension properties (width, height, padding, margin)
- Border properties (border-width, border-radius)
- Visual effects (opacity, transforms)

### Phase 3: CSS Augmentation (Week 5-6)
- Add new CSS variables
- Add new CSS classes
- Full CSS replacement mode
- Comprehensive testing

**Estimated Total: 4-6 weeks**

**Complexity: HIGH**

**Risk: HIGH** (Unity USS internals, edge cases, compatibility)

---

## Hybrid Approach (Recommended)

### Timeline

**Weeks 1-2**: Font Replacement MVP (Phases 1-2)
- Core service implementation
- Validation and error handling
- **Deliverable**: Users can replace fonts

**Week 3**: Test & Polish
- Real-world testing with game bundles
- Documentation
- User feedback

**Weeks 4-5**: Targeted CSS Expansion
- Font properties (font-size, font-weight)
- Opacity (simple float property)
- Padding/margin (common requests)
- **Deliverable**: Most-requested CSS properties

**Week 6+**: Evaluate & Iterate
- Gather user feedback
- Identify next priorities
- Expand based on actual need

---

## Success Criteria

### Phase 1 Success Metrics
- [ ] User can place TTF/OTF in `assets/fonts/` and replace game fonts
- [ ] `fm-skin-builder patch --include fonts` works
- [ ] Replacement report shows fonts replaced
- [ ] No crashes or data corruption
- [ ] Basic validation (format, size)

### Phase 2 Success Metrics
- [ ] Comprehensive font validation
- [ ] Clear error messages for common issues
- [ ] Dry-run mode works correctly
- [ ] Test coverage > 80%
- [ ] Documentation published

### Phase 3 Success Metrics (Optional)
- [ ] CSS font-family property patching works
- [ ] CSS font-size property patching works
- [ ] Font mapping system integrated
- [ ] Examples and recipes published

---

## Risk Mitigation

### Font Format Compatibility
**Risk**: Replaced font doesn't render correctly in Unity
**Mitigation**:
- Test with known-good fonts first
- Validate format matches original
- Provide font conversion tools if needed

### Font Size Issues
**Risk**: Large fonts bloat bundle size
**Mitigation**:
- Warn on fonts > 5MB
- Document font optimization techniques
- Consider font subsetting in future

### Font Name Mismatches
**Risk**: User provides wrong font name, replacement fails silently
**Mitigation**:
- Clear error messages
- List available fonts in catalogue
- Suggest close matches (fuzzy matching)

### Unity Version Differences
**Risk**: Font structure changes between Unity versions
**Mitigation**:
- Test across multiple Unity versions
- Version detection and warnings
- Fallback to safe defaults

---

## Open Questions

1. **Font licensing**: Should we validate font licenses? Warn users?
2. **Font optimization**: Should we offer automatic font subsetting?
3. **Font fallbacks**: How to handle missing font replacements?
4. **WOFF/WOFF2 support**: Should we support web fonts?
5. **Font hinting**: Does Unity preserve font hinting?

---

## Next Steps

1. **Create FontSwapService skeleton** (2-3 hours)
2. **Implement font discovery** (2-3 hours)
3. **Integrate with patch pipeline** (2-3 hours)
4. **Add CLI support** (1-2 hours)
5. **Basic validation** (2-3 hours)
6. **Initial testing** (2-3 hours)

**Total to working prototype: ~12-16 hours**

---

## References

### Related Files
- `fm_skin_builder/services/texture_swap_service.py` - Pattern to follow
- `fm_skin_builder/core/bundle_manager.py:43-51` - Font replacement stub
- `fm_skin_builder/core/catalogue/extractors/font_extractor.py` - Font extraction
- `fm_skin_builder/core/catalogue/models.py` - Font model

### Documentation
- `docs/ARCHITECTURE.md` - System architecture
- `docs/SKIN_FORMAT.md` - Config and mapping formats
- `docs/CLI_GUIDE.md` - CLI reference
- `docs/recipes/` - User guides

### Testing
- `tests/test_texture_swap_service.py` - Pattern for font service tests
- `tests/test_catalogue_models.py` - Model testing patterns

---

## Conclusion

Font replacement is the recommended path forward because:
1. ✅ Faster delivery (2-3 weeks vs 4-6 weeks)
2. ✅ Lower risk (proven pattern, simpler implementation)
3. ✅ Higher user impact (dramatic visual changes)
4. ✅ Leverages existing work (extraction, stub, Python scripts)
5. ✅ Foundation for CSS font properties later

Let's start with Phase 1 and get a working MVP in 2-3 weeks!
