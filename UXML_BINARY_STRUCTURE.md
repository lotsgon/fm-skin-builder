# UXML Binary Structure Documentation

## Complete VTA Element Binary Format

This document describes the complete binary format of Unity's VisualTreeAsset (VTA) elements as discovered through reverse engineering.

### Element Structure (Total: Variable)

```
Offset  Size  Type        Field Name                Description
------  ----  ----------  ------------------------  ---------------------------------
+0      4     int32       m_Id                      Element unique ID
+4      4     int32       m_OrderInDocument         Element order in document
+8      4     int32       m_ParentId                Parent element ID
+12     4     uint32      m_RuleIndex               Style rule index (-1 = 0xFFFFFFFF)

+16     4     int32       m_PickingMode             UI picking mode (0 = Position)
+20     4     int32       m_SkipClone               Skip clone flag (0 = false)
+24     4     int32       m_XmlNamespace            Namespace reference (always -1)
+28     4     int32       (unknown)                 Unknown field (always 0)
+32     4     int32       (unknown)                 Unknown field (always 0)

+36     4     int32       m_Classes.count           Number of CSS classes
+40     var   string[]    m_Classes.data            Array of CSS class names
                                                    Each string:
                                                      - 4 bytes: length
                                                      - N bytes: UTF-8 string
                                                      - 1 byte: null terminator
                                                      - padding to 4-byte boundary

+N      4     int32       m_StylesheetPaths.count   Number of stylesheet paths
+N+4    var   string[]    m_StylesheetPaths.data    Array of stylesheet paths
                                                    (same format as m_Classes)

+M      4     int32       (unknown)                 Unknown field (always 0)
+M+4    4     int32       m_SerializedData          Reference ID for binding data
                                                    (rid value from managedReference)
+M+8    4     int32       (unknown)                 Unknown field (-1 or 0)
+M+12   4     int32       (unknown)                 Unknown field (always 0)

+K      4     int32       m_Type.length             Type name length
+K+4    N     string      m_Type.data               Type name (e.g., "SI.Bindable.BindingRoot")
+K+4+N  1     byte        null terminator
+?      0-3   bytes       padding                   Align to 4-byte boundary

+L      4     int32       m_Name.length             Element name length
+L+4    N     string      m_Name.data               Element name (usually empty)
+L+4+N  1     byte        null terminator           (NOT aligned - last field)

+END    0-3   bytes       element padding           Padding to 4-byte boundary
                                                    (3 bytes in observed examples)
```

## Key Findings

### 1. Identified Fields

**Unknown Section 1 (20 bytes at offset +16-35):**
- `m_PickingMode` (int32): UI picking mode, typically 0
- `m_SkipClone` (int32): Clone skip flag, typically 0
- `m_XmlNamespace` (int32): Namespace reference, always -1
- 2 unknown int32 fields, always 0

**Unknown Section 2 (16 bytes after m_StylesheetPaths):**
- Unknown int32, always 0
- `m_SerializedData` (int32): Reference ID (rid) for binding data
  - Positive values (e.g., 1000, 1001) indicate elements with bindings
  - Negative values (e.g., -2) indicate special cases
- 2 unknown int32 fields, varies (-1 or 0, then 0)

### 2. Important Notes

**m_SerializedData:**
- This field contains the reference ID for Unity's managed reference system
- It points to binding data stored elsewhere in the asset
- This is where `data-binding`, `binding-mappings`, and other UXML attributes are stored
- Critical for preserving element bindings during UXML editing

**String Arrays:**
- All string arrays (m_Classes, m_StylesheetPaths) use 4-byte alignment
- Each string has: length (4 bytes) + data + null terminator + padding

**Element Alignment:**
- Each element is padded to 4-byte boundary
- Observed padding: 3 bytes between consecutive elements

**Element Types:**
- m_Type is stored as binary string, not in UnityPy parsed data
- For VisualElements: type like "SI.Bindable.BindingRoot"
- For TemplateContainers: usually a single space character " "

## Data Not Editable via Text UXML

The following data cannot be modified through text UXML files:
- `m_OrderInDocument`: Internal document ordering
- `m_ParentId`: Internal parent reference
- `m_PickingMode`: Not exposed in UXML syntax
- `m_SkipClone`: Not exposed in UXML syntax
- `m_SerializedData`: Bindings stored in separate managedReferencesRegistry

## Example Binary Hex Dump

Element ID=-277358335 (BindingRoot with one CSS class):
```
Offset  Hex Data                                          Decoded
------  ------------------------------------------------  -----------------------
+0      01 d9 77 ef                                       m_Id = -277358335
+4      01 00 00 00                                       m_OrderInDocument = 1
+8      98 88 00 55                                       m_ParentId = 1426098328
+12     00 00 00 00                                       m_RuleIndex = 0

+16     00 00 00 00                                       m_PickingMode = 0
+20     00 00 00 00                                       m_SkipClone = 0
+24     ff ff ff ff                                       m_XmlNamespace = -1
+28     00 00 00 00                                       (unknown) = 0
+32     00 00 00 00                                       (unknown) = 0

+36     01 00 00 00                                       m_Classes.count = 1
+40     12 00 00 00                                       class[0].length = 18
+44     62 61 73 65 2d 74 65 6d 70 6c 61 74 65 2d        "base-template-"
+54     67 72 6f 77 00 00                                 "grow\0" + 1 byte padding

+60     00 00 00 00                                       m_StylesheetPaths.count = 0

+64     00 00 00 00                                       (unknown) = 0
+68     e8 03 00 00                                       m_SerializedData = 1000
+72     00 00 00 00                                       (unknown) = 0
+76     00 00 00 00                                       (unknown) = 0

+80     01 00 00 00                                       m_Type.length = 1
+84     20 00                                             " \0" (space + null)
+86     00 00                                             2 bytes padding

+88     00 00 00 00                                       m_Name.length = 0
+92     00                                                null terminator

+93     00 00 00                                          3 bytes element padding
```

## Usage in UXML Patching

When patching UXML:
1. **Only modify editable fields:**
   - `m_Classes`: CSS classes from `class` attribute
   - `m_StylesheetPaths`: Stylesheet paths (rarely used)

2. **Preserve internal fields:**
   - `m_Id`, `m_OrderInDocument`, `m_ParentId`: Critical for structure
   - `m_RuleIndex`: Style rule reference
   - All fields in "unknown sections": Unknown purpose, preserve as-is

3. **Handle separate arrays:**
   - VisualElements and TemplateAssets are stored in **separate arrays**
   - Each array has its own size field and must be patched independently

## References

- Unity UI Toolkit Documentation: https://docs.unity3d.com/Manual/UIElements.html
- UnityPy Library: https://github.com/K0lb3/UnityPy
- Discovered through binary analysis and UnityPy attribute comparison
