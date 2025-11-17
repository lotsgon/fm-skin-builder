# Unity VisualTreeAsset Binary Format

## Overview

This document describes the binary structure of Unity's VisualTreeAsset (VTA) files as discovered through reverse engineering Football Manager's UI bundles.

**Status**: Template References Format VERIFIED ✅
**Last Updated**: 2025-11-17
**Test File**: `test_bundles/ui-tiles_assets_all.bundle` → PlayerAttributesSmallBlock (30,504 bytes)

---

## High-Level Structure

```
┌─────────────────────────────────────┐
│ Fixed Header (72 bytes)             │  ← Unity object metadata
│  - Zeros, flags, type ID            │
│  - m_Name length + data             │
│  - Padding to template refs         │
├─────────────────────────────────────┤
│ Template References (variable)      │  ← Metadata for unique templates
│  - Count of unique templates        │
│  - Each template: name + GUID       │
├─────────────────────────────────────┤
│ Visual Elements Array:              │
│  - Count (4 bytes)                  │
│  - TypeTree metadata (40 bytes)     │
│  - Element data (variable)          │
├─────────────────────────────────────┤
│ Template Instances Array:           │
│  - Count (4 bytes)                  │
│  - TypeTree metadata (12 bytes)     │
│  - Element data (variable)          │
└─────────────────────────────────────┘
```

**Key Discoveries**:
1. Array counts are NOT at fixed offsets - they appear immediately before each array's data
2. Template References section contains UNIQUE template types, not instances
3. Header size varies based on m_Name length and number of unique templates

---

## Detailed Format (PlayerAttributesLargeBlock Example)

### Header Section (Variable Size)

```
Offset  Size  Value       Description
------  ----  ----------  -----------
0       12    0x00...     Unknown (all zeros)
12      4     1           Unknown flag/counter
16      4     1           Unknown flag/counter
20      4     11995       Unknown (type ID? version?)
24      4     0           Unknown
28      4     26          m_Name string length
32      26    "Player..." m_Name string data
58      1     0x00        m_Name null terminator
59      1     padding     Align to 4-byte boundary
60      12    0x00...     Padding/unknown (12 bytes)
72      →     ...         Template References Section starts
```

**Header Size**: Variable, ~72 bytes before template references

### Template References Section (Variable Size)

**CRITICAL DISCOVERY**: This section contains metadata for UNIQUE template types referenced by the VTA.

```
Offset  Size  Value       Description
------  ----  ----------  -----------
72      4     6           Count of unique template references
76      var   ...         Template reference 1
        var   ...         Template reference 2
        ...   ...         (etc.)
```

**Each Template Reference Structure**:
```
+0      4     length      Template name string length
+4      var   "name"      Template name (e.g., "AttributesTableSmall")
+?      1     0x00        Null terminator
+?      0-3   padding     Align to 4-byte boundary
+?      4     32          GUID string length (always 32)
+?      32    "guid..."   GUID hex string (32 chars)
+?      1     0x00        Null terminator
+?      0-3   padding     Align to 4-byte boundary
+?      12    0x00...     Unknown padding (12 bytes, all zeros)
```

**Example** (PlayerAttributesSmallBlock):
- 9 template instances in m_TemplateAssets
- 6 unique template references in header
- Unique templates: AttributesTableSmall, FootednessStepperWithBorderCell, etc.

**Header Size**: Variable, depends on:
- m_Name length
- Number of unique template references
- Length of template names

### Visual Elements Array (Offsets 572-7155)

```
Offset  Size  Value       Description
------  ----  ----------  -----------
572     4     44          Array count (m_VisualElementAssets.Length)
576     40    ...         TypeTree metadata for VisualElementAsset

TypeTree breakdown (576-615):
  576     4     27          Unknown (type name length?)
  580     4     1953066581  Unknown (type identifier?)
  584-608 24    ...         Type descriptor data
  612     8     0x00...     Padding/alignment

616     6540  ...         Element binary data (44 elements)
```

**Visual Elements Data**: Each element has variable size (depends on m_Classes, m_StylesheetPaths, etc.)

### Template Assets Array (Offsets 7156-end)

```
Offset  Size  Value       Description
------  ----  ----------  -----------
7156    4     10          Array count (m_TemplateAssets.Length)
7160    12    0x00...     TypeTree metadata (all zeros for templates)

7172    ?     ...         Element binary data (10 template elements)
```

**Template TypeTree**: Only 12 bytes, all zeros. May indicate templates use same structure as visual elements.

---

## Element Binary Format

(Already documented - see UXML_PATCHING_STATUS.md)

Each element (visual or template) uses this format:

```
Offset  Size  Field
------  ----  -----
+0      4     m_Id
+4      4     m_OrderInDocument
+8      4     m_ParentId
+12     4     m_RuleIndex
+16     20    UI behavior fields (5 × int32)
+36     var   m_Classes array (no null terminators)
+?      var   m_StylesheetPaths array (no null terminators)
+?      16    Serialization fields (4 × int32)
+?      var   m_Type string (with null, aligned)
+?      var   m_Name string (with null, NOT aligned)
```

**Key Point**: String arrays use format: `count + [length + data]* + padding`

---

## Critical Findings for Rebuild Approach

### ✅ What We Know

1. **Array Counts Are Embedded**
   - Visual count at offset 572 (for this specific file)
   - Template count at offset 7156 (for this specific file)
   - **NOT** at fixed positions like "offset 152"
   - Position depends on header size

2. **TypeTree Metadata Present**
   - Visual elements: 40 bytes of type information
   - Template elements: 12 bytes (zeros)
   - Critical for Unity to deserialize correctly

3. **Element Binary Format Complete**
   - String array format understood ✅
   - Individual field format understood ✅
   - Size calculation working ✅

### ❓ What We Don't Know Yet

1. **Header Structure (0-571)**
   - What's in offsets 0-11? (all zeros)
   - What's at offset 12, 16? (both = 1)
   - What's at offset 20? (11995 - some ID?)
   - What's between m_Name and visual count?

2. **TypeTree Format**
   - What do the 40 bytes for visual elements represent?
   - Why first value is 27?
   - Why templates only need 12 zero bytes?
   - Is this Unity's TypeTree serialization?

3. **How UnityPy Reads This**
   - How does UnityPy know where arrays start?
   - Does it use TypeTree to navigate?
   - Why does UnityPy's save() break the format?

---

## Implications for Manual Serialization

To manually rebuild a VTA binary:

### Approach 1: Clone Original Structure
```python
1. Read original VTA binary
2. Parse header (up to first count field)
3. Replace m_VisualElementAssets data
   - Keep original TypeTree (40 bytes)
   - Update count
   - Serialize elements
4. Replace m_TemplateAssets data
   - Keep original TypeTree (12 bytes)
   - Update count
   - Serialize elements
```

**Pro**: Preserves all unknown fields
**Con**: Requires finding where visual count starts (varies by m_Name length)

### Approach 2: Full Manual Serialization
```python
1. Build header from scratch
   - Set known fields (m_Name, etc.)
   - Fill unknown fields with zeros or copied values
2. Serialize m_VisualElementAssets
   - Write count
   - Write TypeTree (40 bytes - copy from original?)
   - Write element data
3. Serialize m_TemplateAssets
   - Write count
   - Write TypeTree (12 bytes zeros)
   - Write element data
```

**Pro**: Full control over structure
**Con**: Must understand ALL header fields

---

## Next Steps

### Phase 1: Understanding (Current)
- [x] Locate array counts in binary
- [x] Map high-level structure
- [ ] Decode header fields (0-571)
- [ ] Understand TypeTree format
- [ ] Document footer/padding requirements

### Phase 2: Comparison
- [ ] Compare 2-3 different VTA files
- [ ] Identify what changes between files
- [ ] Identify what stays constant
- [ ] Find patterns in header values

### Phase 3: Implementation
- [ ] Write VTA header parser
- [ ] Write VTA header builder
- [ ] Test round-trip (read → write → compare)
- [ ] Verify Unity can load rebuilt files

---

## Test Data

### PlayerAttributesLargeBlock Stats
- Total size: 29,468 bytes
- Visual elements: 44
- Template assets: 10
- Header size: ~572 bytes
- Visual data: 6,540 bytes (572-7155)
- Template data: ~22,296 bytes (7172-end)

### Offsets Summary
| Item | Offset | Size | Notes |
|------|--------|------|-------|
| Header start | 0 | ~572 | Variable |
| Visual count | 572 | 4 | = 44 |
| Visual TypeTree | 576 | 40 | Type info |
| Visual data | 616 | 6540 | 44 elements |
| Template count | 7156 | 4 | = 10 |
| Template TypeTree | 7160 | 12 | All zeros |
| Template data | 7172 | ~22296 | 10 elements |

---

## Template References - VERIFIED FORMAT ✅

**Discovery Date**: 2025-11-17
**Verification**: Byte-for-byte match on PlayerAttributesSmallBlock (484 bytes, 6 templates)

### Structure

The template references section is more complex than typical Unity serialization. Each template record has variable padding based on name length and MUST align to 12-byte boundaries.

```
Template References Section:
  +0      4 bytes    Template count

  For each template (total size MUST be multiple of 12 bytes):
    +0    4 bytes    Name length (n)
    +4    n bytes    Template name (UTF-8, no terminator)
    +?    variable   Alignment block (depends on n % 4):
                       If n % 4 == 0: nothing here
                       If n % 4 != 0: null terminator + padding to 4-byte boundary
    +?    4 bytes    Separator block (ALWAYS 0x20 0x00 0x00 0x00)
    +?    32 bytes   GUID (32 ASCII hex chars, NO length prefix)
    +?    1 byte     Null terminator
    +?    0-3 bytes  Alignment padding to 4-byte boundary
    +?    variable   Final padding to make total template size % 12 == 0
```

### Critical Details

1. **Name Termination**:
   - If `name_len % 4 == 0`: No terminator, separator block comes immediately after name
   - If `name_len % 4 != 0`: Null terminator (0x00) + padding to reach 4-byte boundary

2. **4-Byte Separator Block**:
   - ALWAYS present after name (and alignment)
   - Always exactly: `0x20 0x00 0x00 0x00` (space + 3 nulls)
   - Discovered through hex analysis - appears between name and GUID

3. **GUID Format**:
   - Fixed 32 bytes (ASCII hex characters)
   - NO length prefix (unlike name)
   - Followed by single null terminator (0x00)
   - Then aligned to 4-byte boundary

4. **12-Byte Alignment**:
   - Total template record size MUST be multiple of 12
   - Padding formula: `padding = 12 - (size_before_padding % 12)`
   - Padding is all zeros

### Example: Template with name_len=20 (divisible by 4)

```
Offset  Bytes              Description
------  -----------------  -----------
0       14 00 00 00        Name length = 20
4       41 74 74 ...       "AttributesTableSmall" (20 bytes)
24      20 00 00 00        Separator block (space + 3 nulls)
28      33 66 64 33 ...    GUID "3fd3642a7a..." (32 bytes)
60      00                 Null terminator
61      00 00 00           Padding to 4-byte boundary
64      00 00 00 00        Final padding (8 bytes total)
68      00 00 00 00
72      [next template]    Total: 72 bytes (72 % 12 == 0 ✓)
```

### Example: Template with name_len=31 (NOT divisible by 4)

```
Offset  Bytes              Description
------  -----------------  -----------
0       1f 00 00 00        Name length = 31
4       46 6f 6f 74 ...    "FootednessStepperWithBorderCell" (31 bytes)
35      00                 Null terminator (because 31 % 4 != 0)
36      [already aligned]  31 + 1 = 32, divisible by 4
36      20 00 00 00        Separator block (space + 3 nulls)
40      31 33 61 36 ...    GUID "13a62bdd03..." (32 bytes)
72      00                 Null terminator
73      00 00 00           Padding to 4-byte boundary
76      00 00 00 00        Final padding (8 bytes total)
80      00 00 00 00
84      [next template]    Total: 84 bytes (84 % 12 == 0 ✓)
```

### Parser Implementation

See `fm_skin_builder/core/uxml/vta_header_parser.py`:
- `parse_vta_header()` - Extracts all VTA metadata
- `_parse_template_references()` - Parses template refs section (VERIFIED)
- `serialize_template_references()` - Reconstructs byte-perfect output

**Verification**: The serializer produces byte-for-byte identical output to Unity's original format.

---

## String Array Format - VERIFIED ✅

**Discovery Date**: 2025-11-17
**Verification**: 100% parsing success across 55 elements (49 visual + 6 template) in 10 VTAs

### Conditional Null Terminator Pattern

Unity's string array serialization uses a **conditional null terminator** based on alignment:

```
For each string in array:
  1. Write length (4 bytes, little-endian)
  2. Write string data (N bytes, UTF-8)
  3. IF (current_position % 4 == 0):
       - Already aligned, NO null terminator
       - Continue to next string/field
     ELSE:
       - Add null terminator (0x00)
       - Pad with 0x00 until (position % 4 == 0)
```

### Examples

#### String Ending Aligned (28 bytes at position 840)
```
Position 836: Length field (0x1C 0x00 0x00 0x00 = 28)
Position 840: String data "margin-left-global-gap-small" (28 bytes)
Position 868: Next length field (already 4-byte aligned, NO null)
```

#### String Not Aligned (25 bytes at position 808)
```
Position 804: Length field (0x19 0x00 0x00 0x00 = 25)
Position 808: String data "body-regular-14px-regular" (25 bytes)
Position 833: Null terminator (0x00)
Position 834: Padding (0x00 0x00) to align to 836
Position 836: Next length field
```

### Key Points

1. **Per-String Alignment**: Each string is aligned BEFORE the next length field, not at the end of the array
2. **Conditional Null**: Null terminator is only added if string doesn't end on 4-byte boundary
3. **No Null When Aligned**: If string length causes natural 4-byte alignment, no null is added
4. **Padding After Null**: After null (if added), pad to next 4-byte boundary

### Implementation

Located in `fm_skin_builder/core/uxml/uxml_element_parser.py`:

**Parser**:
```python
pos += str_len  # Move past string data

if pos % 4 == 0:
    # Already aligned, no null needed
    pass
else:
    pos += 1  # Null terminator
    # Pad to 4-byte boundary
    remainder = pos % 4
    if remainder != 0:
        pos += 4 - remainder
```

**Serializer**:
```python
data.extend(string_bytes)

if len(data) % 4 == 0:
    # Already aligned, no null
    pass
else:
    data.append(0)  # Null terminator
    while len(data) % 4 != 0:
        data.append(0)  # Padding
```

### Affected Arrays

This pattern applies to:
- `m_Classes` string array in elements
- `m_StylesheetPaths` string array in elements
- Template names in template references (though they always have null + padding)

**Success Rate**: This discovery enabled 100% parsing accuracy across all tested VTAs, up from ~77% before.

---

## Resources

**Unity Documentation**:
- [TypeTree serialization](https://docs.unity3d.com/Manual/class-SerializedFile.html)
- [VisualTreeAsset API](https://docs.unity3d.com/ScriptReference/UIElements.VisualTreeAsset.html)

**Tools**:
- UnityPy - Reading VTA data
- Our element parser - `fm_skin_builder/core/uxml/uxml_element_parser.py`

**Test Files**:
- `test_bundles/ui-tiles_assets_all.bundle`
- `skins/new_skin/panels/PlayerAttributesLargeBlock.uxml`

---

*This format is being actively researched. Updates will be added as discoveries are made.*
