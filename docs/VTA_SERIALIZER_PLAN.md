# VTA Binary Serializer Implementation Plan

## Status: Ready to Implement
**Last Updated**: 2025-11-16
**Prerequisite**: VTA binary format fully understood (see VTA_BINARY_FORMAT.md)

---

## Objective

Build a manual VTA binary serializer that can:
1. Read original VTA binary
2. Parse UXML modifications
3. Rebuild VTA binary with structural changes
4. Preserve all Unity-specific metadata

**Why Manual**: UnityPy's save() produces invalid bundles. We must serialize ourselves.

---

## Approach: Clone + Modify

**Strategy**: Copy original binary structure, replace only element data.

**Benefits**:
- Preserves unknown header fields
- Preserves TypeTree metadata
- Preserves template references section
- Minimal risk of breaking Unity's deserializer

---

## Implementation Steps

### Phase 1: VTA Header Parser

**File**: `fm_skin_builder/core/uxml/vta_header_parser.py`

**Purpose**: Extract all header data from original VTA

```python
class VTAHeader:
    """Represents parsed VTA header."""

    # Fixed header (0-72)
    fixed_header: bytes  # 72 bytes - copy verbatim

    # Template references section
    template_refs: List[TemplateReference]

    # Calculated offsets
    visual_array_offset: int
    template_array_offset: int

class TemplateReference:
    """Single template reference metadata."""
    name: str
    guid: str

def parse_vta_header(raw_data: bytes) -> VTAHeader:
    """Parse VTA header from binary data."""
    # Read fixed header (0-72)
    # Parse template references
    # Find where visual array starts
    # Return structured header
```

**Implementation**:
1. Copy bytes 0-72 (fixed header)
2. Parse template count at offset 72
3. Parse each template reference:
   - Read name (length + string + null + align)
   - Read GUID (length + string + null + align)
   - Read padding (12 bytes)
4. Calculate visual array offset (after last template ref)

**Output**: Complete header structure ready for serialization

### Phase 2: Element Serializer

**File**: `fm_skin_builder/core/uxml/vta_element_serializer.py`

**Purpose**: Serialize element lists into VTA arrays

**Already Done**: Element binary format in `uxml_element_parser.py`

**New Functions Needed**:

```python
def serialize_visual_elements_array(
    elements: List[UXMLElementBinary],
    typetree_metadata: bytes  # 40 bytes from original
) -> bytes:
    """
    Serialize visual elements array.

    Format:
      count (4 bytes)
      TypeTree metadata (40 bytes) - copied from original
      element data (variable)
    """
    data = bytearray()
    data.extend(struct.pack('<i', len(elements)))
    data.extend(typetree_metadata)

    for elem in elements:
        data.extend(elem.to_bytes())  # Already implemented!

    return bytes(data)

def serialize_template_assets_array(
    elements: List[UXMLElementBinary],
    typetree_metadata: bytes  # 12 bytes from original
) -> bytes:
    """
    Serialize template assets array.

    Format:
      count (4 bytes)
      TypeTree metadata (12 bytes) - copied from original
      element data (variable)
    """
    data = bytearray()
    data.extend(struct.pack('<i', len(elements)))
    data.extend(typetree_metadata)

    for elem in elements:
        data.extend(elem.to_bytes())

    return bytes(data)
```

### Phase 3: VTA Builder

**File**: `fm_skin_builder/core/uxml/vta_builder.py`

**Purpose**: Combine all parts into complete VTA binary

```python
class VTABuilder:
    """Builds complete VTA binary from components."""

    def __init__(self, original_vta_binary: bytes):
        """Initialize with original VTA for metadata."""
        self.header = parse_vta_header(original_vta_binary)

        # Extract TypeTree metadata from original
        self.visual_typetree = self._extract_visual_typetree(original_vta_binary)
        self.template_typetree = self._extract_template_typetree(original_vta_binary)

    def build(
        self,
        visual_elements: List[UXMLElementBinary],
        template_elements: List[UXMLElementBinary]
    ) -> bytes:
        """Build complete VTA binary."""
        data = bytearray()

        # 1. Write fixed header (0-72)
        data.extend(self.header.fixed_header)

        # 2. Write template references section
        data.extend(self._serialize_template_refs())

        # 3. Write visual elements array
        visual_array = serialize_visual_elements_array(
            visual_elements,
            self.visual_typetree
        )
        data.extend(visual_array)

        # 4. Write template assets array
        template_array = serialize_template_assets_array(
            template_elements,
            self.template_typetree
        )
        data.extend(template_array)

        return bytes(data)

    def _serialize_template_refs(self) -> bytes:
        """Serialize template references section."""
        data = bytearray()
        data.extend(struct.pack('<i', len(self.header.template_refs)))

        for ref in self.header.template_refs:
            # Name
            name_bytes = ref.name.encode('utf-8')
            data.extend(struct.pack('<i', len(name_bytes)))
            data.extend(name_bytes)
            data.append(0)  # null
            while len(data) % 4 != 0:
                data.append(0)  # align

            # GUID
            guid_bytes = ref.guid.encode('utf-8')
            data.extend(struct.pack('<i', len(guid_bytes)))
            data.extend(guid_bytes)
            data.append(0)  # null
            while len(data) % 4 != 0:
                data.append(0)  # align

            # Padding (12 bytes zeros)
            data.extend(b'\x00' * 12)

        return bytes(data)
```

### Phase 4: Integration with Binary Patcher

**File**: `fm_skin_builder/core/uxml/uxml_binary_patcher_v2.py`

**Modify**: Add rebuild method using VTABuilder

```python
def apply_uxml_to_vta_binary(
    self,
    raw_data: bytes,
    imported_data: Dict[str, Any],
    visual_elements: List[Any],
    template_assets: List[Any]
) -> Optional[bytes]:
    """Apply UXML changes by rebuilding VTA binary."""

    # Try in-place patching first (for CSS-only changes)
    if self._can_patch_in_place(imported_data):
        # Existing in-place logic...
        pass

    # Fall back to rebuild approach (for structural changes)
    return self._rebuild_vta(raw_data, imported_data, visual_elements, template_assets)

def _rebuild_vta(
    self,
    raw_data: bytes,
    imported_data: Dict[str, Any],
    visual_elements: List[Any],
    template_assets: List[Any]
) -> bytes:
    """Rebuild VTA from scratch using manual serialization."""
    from .vta_builder import VTABuilder

    # Parse elements from imported UXML
    new_visual = self._build_elements_from_uxml(
        imported_data['m_VisualElementAssets']
    )
    new_template = self._build_elements_from_uxml(
        imported_data['m_TemplateAssets']
    )

    # Build VTA binary
    builder = VTABuilder(raw_data)
    return builder.build(new_visual, new_template)
```

---

## Testing Strategy

### Test 1: Pure Round-Trip
**Goal**: Verify serializer produces identical output

```python
# 1. Load original VTA
original = read_vta_binary('test_bundles/ui-tiles_assets_all.bundle', 'PlayerAttributesSmallBlock')

# 2. Parse it
elements_visual, elements_template = parse_vta_elements(original)

# 3. Rebuild it (no modifications)
builder = VTABuilder(original)
rebuilt = builder.build(elements_visual, elements_template)

# 4. Compare
if rebuilt == original:
    print("✅ Perfect round-trip!")
else:
    print(f"❌ Size diff: {len(rebuilt)} vs {len(original)}")
    find_first_difference(rebuilt, original)
```

**Success Criteria**: Byte-for-byte identical output

### Test 2: CSS Changes Only
**Goal**: Verify modified m_Classes work

```python
# Modify one element's classes
elements_visual[0].m_Classes = ['new-class', 'test']

# Rebuild
rebuilt = builder.build(elements_visual, elements_template)

# Load in UnityPy
env = UnityPy.load(rebuilt)
# Verify it loads without errors
```

**Success Criteria**: UnityPy loads without errors

### Test 3: Element Reordering
**Goal**: Verify structural changes work

```python
# Swap two elements (change m_OrderInDocument)
elements_visual[5], elements_visual[10] = elements_visual[10], elements_visual[5]

# Rebuild
rebuilt = builder.build(elements_visual, elements_template)

# Test in-game
# Copy to FM, check if elements appear in new order
```

**Success Criteria**: Game loads without crash, elements in new order

### Test 4: Footedness Swap
**Goal**: End-to-end test of structural modifications

```python
# Load modified UXML
uxml_doc = import_uxml('skins/new_skin/panels/PlayerAttributesLargeBlock.uxml')

# Find left/right foot elements
left_foot = find_element_by_name(uxml_doc, 'LeftFootedness')
right_foot = find_element_by_name(uxml_doc, 'RightFootedness')

# Swap positions (m_OrderInDocument)
left_foot.m_OrderInDocument, right_foot.m_OrderInDocument =
    right_foot.m_OrderInDocument, left_foot.m_OrderInDocument

# Rebuild VTA
rebuilt = builder.build(visual_elements, template_elements)

# Inject into bundle and test
```

**Success Criteria**: Left/right foot attributes appear swapped in-game

---

## Error Handling

### Common Issues

1. **Size Mismatch**
   - Problem: Rebuilt VTA larger/smaller than original
   - Debug: Compare section sizes (header, template refs, arrays)
   - Fix: Check alignment, padding

2. **UnityPy Load Failure**
   - Problem: "Negative length" or deserialization error
   - Debug: Check array counts, TypeTree metadata
   - Fix: Ensure counts match element data

3. **Game Crash**
   - Problem: Bundle loads but game crashes
   - Debug: Binary comparison with working bundle
   - Fix: Verify all unknown fields preserved

---

## Code Locations

**New Files to Create**:
- `fm_skin_builder/core/uxml/vta_header_parser.py`
- `fm_skin_builder/core/uxml/vta_element_serializer.py`
- `fm_skin_builder/core/uxml/vta_builder.py`

**Files to Modify**:
- `fm_skin_builder/core/uxml/uxml_binary_patcher_v2.py` (add rebuild method)

**Existing Code to Reuse**:
- `fm_skin_builder/core/uxml/uxml_element_parser.py` (element.to_bytes())
- `fm_skin_builder/core/uxml/uxml_importer.py` (UXML parsing)

---

## Success Metrics

- [ ] Pure round-trip produces identical binary
- [ ] Modified VTA loads in UnityPy
- [ ] CSS-only changes work in-game
- [ ] Element reordering works in-game
- [ ] Footedness swap works in-game
- [ ] No bundle size bloat (stays ~5MB)

---

## Next Session Checklist

1. Create `vta_header_parser.py`
2. Implement `parse_vta_header()` function
3. Write tests for header parsing
4. Create `vta_builder.py`
5. Implement `VTABuilder.build()` method
6. Run Test 1 (pure round-trip)
7. Debug any size/format mismatches
8. Run Test 2 (CSS changes)
9. Run Test 3 (reordering)
10. Run Test 4 (footedness swap)

---

**Estimated Time**: 2-3 hours of focused implementation

**Risk Level**: Medium (format is understood, but devils in the details)

**Fallback**: Option A (in-place patcher) works for CSS-only changes

---

*This plan is ready to execute. All prerequisites are met.*
