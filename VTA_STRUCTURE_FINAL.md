# Unity VisualTreeAsset (VTA) Complete Binary Structure

## Overview

This document describes the complete binary layout of Unity's VisualTreeAsset files as stored in Football Manager's asset bundles.

## Complete Binary Layout

```
Offset      Size    Type            Description
─────────────────────────────────────────────────────────────────────────
0-11        12      Various         Header part 1 (metadata)
12-15       4       int32           m_TemplateAssets count
16-151      136     Various         Header part 2 (metadata, strings, etc.)
152-155     4       int32           m_VisualElementAssets count
156-195     40      TypeInfo        Visual elements type information
196-391     196     Elements        Visual elements array data
                                    └─ Element 0: offset 196-291 (96 bytes)
                                    └─ Element 1: offset 292-391 (100 bytes)
392+        var     Elements        Template assets array data
                                    └─ Element 0: offset 392-511 (120 bytes)
                                    └─ (continues...)
───────────────────────────────────────────────────────────────────────
```

## Key Findings

### 1. Array Count Locations

**CRITICAL:** Both array counts are stored in the HEADER, not between arrays!

- **Template assets count**: Offset 12 (before visual elements)
- **Visual elements count**: Offset 152 (standard array header)

### 2. Array Storage

Arrays are stored **sequentially** without intermediate count fields:
1. Visual elements array (uses count at offset 152)
2. Template assets array (uses count from offset 12)
3. NO separate count field between arrays

### 3. Type Information

- **Visual elements**: Type info at offset 156-195 (40 bytes)
- **Template assets**: No separate type info section (shares structure)

### 4. Element Structure

Each element follows the structure documented in UXML_BINARY_STRUCTURE.md:
- Fixed fields (36 bytes)
- Variable string arrays (m_Classes, m_StylesheetPaths)
- Serialization fields (16 bytes)
- Type and name strings
- Padding to 4-byte alignment

## Implications for Patching

### When Modifying Arrays:

**Visual Elements:**
1. Update count at offset 152
2. Update type info if needed (offset 156-195)
3. Write elements starting at offset 196
4. Calculate new offset for template assets

**Template Assets:**
1. Update count at offset 12
2. Write elements after visual elements end
3. NO separate type info to update

### Data Preservation:

Must preserve:
- Header (offsets 0-151)
- Type info (offsets 156-195)
- All data after arrays

### Size Changes:

When arrays change size:
- Visual array changes: Affects where template array starts
- Template array changes: Affects total file size
- Must shift subsequent data appropriately

## Example: AboutClubCard

```
Actual values:
  Offset 12:  Template count = 1
  Offset 152: Visual count = 2

Layout:
  0-11:      Header
  12-15:     Value: 1 (template count)
  16-151:    Header continuation
  152-155:   Value: 2 (visual count)
  156-195:   Type info (40 bytes)
  196-291:   Visual Element 0 (ID 1426098328)
  292-391:   Visual Element 1 (ID -277358335)
  392-511:   Template Element 0 (ID 793018003)
  512+:      Footer/other data
```

## Rebuilding Strategy

### Correct Approach:

```python
1. Keep header (0-11)
2. Update template count (offset 12)
3. Keep header part 2 (16-151)
4. Update visual count (offset 152)
5. Keep/update type info (156-195)
6. Write visual elements (196+)
7. Write template elements (after visual)
8. Append footer data
```

### Common Mistakes:

❌ Looking for template count between arrays (doesn't exist)
❌ Treating all elements as one array (they're separate)
❌ Forgetting to update offset 12 when changing template count
❌ Not preserving type info section (156-195)

## References

- Element structure: See UXML_BINARY_STRUCTURE.md
- Field details: See earlier analysis documents
- Unity TypeTree documentation: Unity serialization format
