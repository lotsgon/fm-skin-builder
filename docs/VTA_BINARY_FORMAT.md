# Unity VisualTreeAsset Binary Format

## Overview

This document describes the binary structure of Unity's VisualTreeAsset (VTA) files as discovered through reverse engineering Football Manager's UI bundles.

**Status**: Work in progress (Phase 1 - Structure Discovery)
**Last Updated**: 2025-11-16
**Test File**: `test_bundles/ui-tiles_assets_all.bundle` → PlayerAttributesLargeBlock (29,468 bytes)

---

## High-Level Structure

```
┌─────────────────────────────────────┐
│ Header (variable size)              │  ← Contains m_Name, metadata
├─────────────────────────────────────┤
│ Visual Elements Array:              │
│  - Count (4 bytes)                  │
│  - TypeTree metadata (40 bytes)     │
│  - Element data (variable)          │
├─────────────────────────────────────┤
│ Template Assets Array:              │
│  - Count (4 bytes)                  │
│  - TypeTree metadata (12 bytes)     │
│  - Element data (variable)          │
└─────────────────────────────────────┘
```

**Key Discovery**: Array counts are NOT at fixed offsets! They appear immediately before each array's data.

---

## Detailed Format (PlayerAttributesLargeBlock Example)

### Header Section (Offsets 0-571)

```
Offset  Size  Value       Description
------  ----  ----------  -----------
0       12    0x00...     Unknown (all zeros)
12      4     1           Unknown flag/counter
16      4     1           Unknown flag/counter
20      4     11995       Unknown
24      4     0           Unknown
28      4     26          m_Name string length
32      26    "Player..." m_Name string data
58      ?     ...         Unknown header data continues
...
572     →     (Visual count starts here)
```

**Header Size**: Variable, depends on m_Name length and other metadata

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
