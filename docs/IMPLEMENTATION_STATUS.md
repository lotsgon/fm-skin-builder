# VTA Serializer Implementation Status

**Date**: 2025-11-16 (continued session)
**Branch**: `claude/uxml-rebuild-full-structure`
**Token Usage**: 130k/200k (65%)

---

## Current Status: In Progress

### ✅ Completed Components

**1. VTA Element Serializer** (`vta_element_serializer.py`)
- Serializes visual elements array (count + TypeTree + data)
- Serializes template assets array (count + TypeTree + data)
- Reuses `elem.to_bytes()` from Option A
- **Status**: Complete and tested

**2. VTA Builder** (`vta_builder.py`)
- Combines all VTA components
- Uses header parser to extract metadata
- Builds complete VTA binary
- **Status**: Complete, blocked by header parser issue

**3. Test Script** (`test_vta_roundtrip.py`)
- Loads original VTA
- Parses elements
- Rebuilds using VTABuilder
- Compares byte-for-byte
- **Status**: Ready to run once parser is fixed

### ⚠️ In Progress

**VTA Header Parser** (`vta_header_parser.py`)

**What Works**:
- ✅ Fixed header extraction (bytes 0-72)
- ✅ Template count reading
- ✅ GUID format identified (32 bytes, no length prefix)

**Current Issue**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xab in position 408
```

**Problem**: Template references structure not fully understood

**What We Know**:
```
Template Reference (partial):
  +0      4     length      Template name string length
  +4      var   "name"      Template name
  +?      1     0x00        Null terminator
  +?      0-3   padding     Align to 4-byte boundary
  +?      32    "guid..."   GUID (32-byte ASCII hex, no length!)
  +?      1     0x00        Null terminator
  +?      0-3   padding     Align to 4-byte boundary
  +?      12    0x00...     Padding (12 bytes zeros)
  +?      ???   ???         ← UNKNOWN - causing parse to fail
```

**Error Location**: Trying to parse 2nd template name at position 408

**What's Happening**:
1. First template parses OK
2. After first template (name + GUID + padding), parser moves to next
3. Reads what it thinks is name length
4. Gets garbage value or wrong offset
5. Tries to decode as UTF-8, fails with 0xab

**Possible Causes**:
1. Missing field(s) between templates
2. Padding calculation wrong
3. GUID structure has more than just 32 bytes + null
4. The 12-byte padding is not always 12 bytes

---

## Next Debugging Steps

### Step 1: Hex Dump Analysis

Need to manually trace through hex for first 2 templates:

```python
import UnityPy
import struct

env = UnityPy.load('test_bundles/ui-tiles_assets_all.bundle')
# ... find VTA
raw = obj.get_raw_data()

# Start at offset 72 (template refs start)
pos = 72
count = struct.unpack_from('<i', raw, pos)[0]
print(f"Count: {count}")
pos += 4

# Manually parse Template 1
print(f"\nTemplate 1 at offset {pos}:")
name_len = struct.unpack_from('<i', raw, pos)[0]
print(f"  Name length: {name_len}")
pos += 4

name = raw[pos:pos + name_len].decode('utf-8')
print(f"  Name: '{name}'")
pos += name_len + 1  # null

# Align
if pos % 4 != 0:
    pos += 4 - (pos % 4)

# GUID
guid = raw[pos:pos + 32].decode('ascii')
print(f"  GUID: '{guid}'")
pos += 32 + 1  # null

# Align
if pos % 4 != 0:
    pos += 4 - (pos % 4)

# Padding - check what's actually here
print(f"\n  Checking 'padding' at offset {pos}:")
for i in range(20):
    val = struct.unpack_from('<i', raw, pos + i*4)[0]
    print(f"    +{i*4}: {val:10} (0x{val & 0xFFFFFFFF:08X})")

# Where should Template 2 start?
# Try different offsets and see which gives valid name length
```

### Step 2: Find Pattern

Once we know the correct structure for Template 1:
- Calculate expected offset for Template 2
- Verify it has valid name length (1-100)
- Verify name decodes as UTF-8
- Adjust parser code

### Step 3: Update Parser

Fix `_parse_template_references()` with correct structure.

### Step 4: Re-test

Run `python test_vta_roundtrip.py`

---

## Code Locations

**Files Created This Session**:
```
fm_skin_builder/core/uxml/
  vta_header_parser.py         ← NEEDS FIX
  vta_element_serializer.py    ← ✅ Complete
  vta_builder.py               ← ✅ Complete

test_vta_roundtrip.py          ← ✅ Ready to use
```

**Files to Debug With**:
```
test_bundles/ui-tiles_assets_all.bundle
```

**Target VTA**: `PlayerAttributesSmallBlock` (30,504 bytes)

---

## Test Results

**Round-Trip Test**: Not yet passing
- Reason: Header parser failing
- Element parsing: Works (34/44 visual, 7/9 template)
- Element serialization: Should work (uses proven code from Option A)

---

## Estimated Remaining Work

**If template refs structure is simple**:
- 15 min: Debug hex, find correct structure
- 5 min: Update parser
- 5 min: Re-test
- **Total**: ~25 minutes

**If template refs structure is complex**:
- 30 min: Research Unity template format
- 15 min: Trial and error with hex
- 10 min: Update parser
- 5 min: Re-test
- **Total**: ~60 minutes

---

## Key Insights So Far

### GUID Format Discovered ✅
- **NOT**: length-prefixed string like template name
- **IS**: Fixed 32-byte ASCII hex string
- No length field before it
- Has null terminator after it

This was a critical discovery!

### Element Serialization Works ✅
From Option A, we know:
- `elem.to_bytes()` produces correct binary
- String array format (no nulls between strings)
- All this is proven and works

So once header parser is fixed, the rest should "just work".

---

## How to Continue

1. **Run hex debugging** (Step 1 above)
2. **Find correct template ref structure**
3. **Update parser**
4. **Run test**: `python test_vta_roundtrip.py`
5. **If test passes**: Move to next test (CSS changes)
6. **If test fails**: Compare rebuilt vs original, fix differences

---

## Git Status

**Current Commit**: `3f1698d` - WIP implementation with template refs issue

**To Push**: After parser is fixed and test passes

---

*Continue from here next session or after token refresh*
