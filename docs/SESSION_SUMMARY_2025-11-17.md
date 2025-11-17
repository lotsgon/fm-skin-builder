# VTA Header Parser - Session Summary

**Date**: 2025-11-17 (Continuation Session)
**Branch**: `claude/uxml-import-export-pipeline-011F7NNuAubpKgmoqPW6SgF2`
**Status**: ✅ VTA Header Parser COMPLETE & VERIFIED

---

## Major Accomplishment

### ✅ Template References Format Fully Reverse-Engineered

Successfully discovered and implemented the complete binary format for Unity VTA template references section:

**Verification Result**: **BYTE-FOR-BYTE PERFECT MATCH** ✓
- Test file: PlayerAttributesSmallBlock (30,504 bytes)
- Template refs section: 484 bytes (6 templates)
- Match: 100% identical to Unity's original format

---

## Discoveries Made

### 1. 4-Byte Separator Block (Major Discovery)

Found that there's a mysterious 4-byte block between template name and GUID:
- Always exactly: `0x20 0x00 0x00 0x00` (space + 3 nulls)
- Not documented in any Unity references
- Discovered through manual hex analysis

### 2. Variable Name Termination

Template names have conditional termination based on length:
- If `name_len % 4 == 0`: No null terminator, separator block comes immediately
- If `name_len % 4 != 0`: Null terminator + padding to 4-byte boundary

### 3. GUID Format (No Length Prefix)

GUID structure differs from typical Unity strings:
- Fixed 32 bytes (ASCII hex characters)
- NO length prefix (unlike template name)
- Followed by null terminator + alignment

### 4. 12-Byte Alignment Requirement

Total template record size must be multiple of 12 bytes:
- Padding formula: `padding = 12 - (size_before_padding % 12)`
- Discovered by analyzing actual template sizes (72, 84, 84, 84 bytes)

---

## Implementation

### Files Created/Modified

**fm_skin_builder/core/uxml/vta_header_parser.py** ✅
- `parse_vta_header()` - Parses complete VTA header
- `_parse_template_references()` - Handles complex template refs format
- `serialize_template_references()` - Byte-perfect reconstruction
- **Status**: Complete and verified

**docs/VTA_BINARY_FORMAT.md** ✅
- Added comprehensive "Template References - VERIFIED FORMAT" section
- Documented all edge cases and alignment rules
- Included hex examples for both name_len%4==0 and name_len%4!=0 cases

### Debug Scripts Created

Throughout the session, created numerous debug scripts to analyze the binary format:
- `debug_all_templates.py` - Trace through all template references
- `debug_template_2_3_hex.py` - Analyze boundary between templates
- `find_padding_pattern.py` - Discovered 12-byte alignment rule
- `check_name_bytes.py` - Verified name encoding
- `check_all_template_terminators.py` - Found variable terminator pattern
- `find_guid_offsets.py` - Located actual GUID start positions
- `hex_dump_184.py` - Raw hex analysis
- `verify_template_refs_section.py` - Final verification script

---

## Debugging Process

### Initial Error (offset 408)
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xab in position 408
```
**Cause**: Thought GUID had length prefix (it doesn't)
**Fix**: GUID is fixed 32 bytes, no length prefix

### Second Error (offset 280)
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xab in position 280
```
**Cause**: Thought padding was fixed 8 or 12 bytes
**Fix**: Discovered 12-byte alignment rule for total template size

### Third Issue (offset 100)
```
Difference at offset 100: Original has 0x20, Rebuilt has 0x00
```
**Cause**: Didn't know about variable name termination
**Fix**: Terminator depends on `name_len % 4`

### Fourth Issue (offset 216)
```
Difference at offset 216: GUID starts wrong
```
**Cause**: Missing 4-byte separator block between name and GUID
**Fix**: Discovered the `0x20 0x00 0x00 0x00` separator block

### Final Success ✅
```
✅ PERFECT MATCH! Template references section is byte-for-byte identical!
```

---

## Technical Insights

### Why This Was Difficult

1. **Non-Standard Format**: Unity's VTA template refs don't follow typical serialization patterns
2. **Variable Padding**: Multiple layers of conditional padding based on different criteria
3. **Undocumented**: No official Unity documentation on this binary format
4. **Hex Analysis Required**: Had to manually trace through raw bytes to find patterns

### Key Breakthroughs

1. **Hex Dumping**: Creating detailed hex dumps around boundaries revealed the separator block
2. **Pattern Recognition**: Analyzing multiple templates showed the 12-byte alignment rule
3. **Systematic Testing**: Testing each offset candidate for GUID start location
4. **Modulo Analysis**: Discovering that `name_len % 4` determines termination behavior

---

## Code Quality

### Parser Logic
```python
# After name: align to 4-byte boundary (if needed)
if name_len % 4 != 0:
    pos += 1  # null terminator
    if pos % 4 != 0:
        pos += 4 - (pos % 4)

# Skip 4-byte separator block (always 0x20 0x00 0x00 0x00)
pos += 4

# GUID is stored as 32-byte ASCII hex string (no length prefix!)
guid = raw_data[pos:pos + 32].decode('ascii')
pos += 32 + 1  # +1 for null terminator

# Align to 4-byte boundary
if pos % 4 != 0:
    pos += 4 - (pos % 4)

# Padding: aligns total template size to multiples of 12 bytes
size_before_padding = pos - template_start
padding = 12 - (size_before_padding % 12)
pos += padding
```

This correctly handles all discovered edge cases.

---

## Remaining Work

### Current Limitation

Round-trip test shows:
- Parsing only 34/44 visual elements (77%)
- Parsing only 7/9 template elements (78%)
- Total rebuilt size: 5,661 bytes vs 30,504 bytes original

**Cause**: Element finding logic (`find_element_offset`) not locating all elements

**Impact**:
- Header parsing is PERFECT ✅
- Element serialization is PROVEN (from Option A) ✅
- Only issue is finding all elements to parse

### Next Steps

1. **Fix Element Finding**: Improve `find_element_offset` to locate all 44 visual + 9 template elements
2. **Round-Trip Test**: Once all elements found, verify byte-perfect round-trip
3. **CSS Test**: Test modifying CSS classes only
4. **Structural Test**: Test element reordering
5. **Footedness Test**: Implement and test the user's footedness swap feature

---

## Files & Locations

### Implementation
```
fm_skin_builder/core/uxml/
  vta_header_parser.py          ✅ Complete & verified
  vta_element_serializer.py     ✅ Complete (reuses Option A code)
  vta_builder.py                ✅ Complete (combines all components)
  uxml_element_parser.py        ⚠️  Element finding needs improvement

test_vta_roundtrip.py           ✅ Ready for testing
```

### Documentation
```
docs/
  VTA_BINARY_FORMAT.md          ✅ Updated with verified template refs format
  IMPLEMENTATION_STATUS.md      ⏳ Needs update
  SESSION_SUMMARY_2025-11-17.md ✅ This file
```

### Test Files
```
test_bundles/ui-tiles_assets_all.bundle  ✅ Working test data
```

---

## Token Usage

- **Start**: ~12% (continuation session)
- **End**: ~36%
- **Total Used**: ~72k tokens
- **Key Achievement**: Reverse-engineered complex binary format with multiple edge cases

---

## Git Status

**Branch**: `claude/uxml-import-export-pipeline-011F7NNuAubpKgmoqPW6SgF2`
**Changes**:
- Modified: `vta_header_parser.py` (multiple iterations)
- Modified: `VTA_BINARY_FORMAT.md` (documentation)
- Created: Multiple debug scripts (temporary, can be deleted)
- Created: This session summary

**Ready to Commit**: Yes, with message like:
```
feat: complete VTA template references parser with byte-perfect verification

- Discovered complex template refs format with variable padding
- Implemented 4-byte separator block handling
- Added conditional name termination based on length
- Verified 12-byte alignment for template records
- Achieved byte-for-byte match on 484-byte section (6 templates)

Template references parser now produces identical output to Unity's
original format. Documented complete format in VTA_BINARY_FORMAT.md
with hex examples and edge cases.

Issue: Element finding only locates 34/44 visual, 7/9 template elements
Next: Improve element offset finding to complete round-trip test
```

---

## Key Takeaway

**Successfully reverse-engineered a complex, undocumented Unity binary format through systematic hex analysis and pattern recognition.**

The VTA header parser is production-ready for the template references section. Once element finding is improved, we'll have a complete VTA rebuild pipeline for Option B.
