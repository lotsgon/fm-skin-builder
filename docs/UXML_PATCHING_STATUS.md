# UXML Patching Status & Roadmap

## Current State (as of 2025-11-16)

### ✅ What Works: In-Place Binary Patcher (Option A)

The in-place binary patcher successfully modifies **CSS classes only** in UXML files:

- **Branch**: `claude/uxml-import-export-pipeline-011F7NNuAubpKgmoqPW6SgF2`
- **Status**: ✅ Working and verified in-game
- **Capability**: Modify m_Classes arrays without changing binary structure

#### Key Achievements

1. **Binary Format Discovery** - Reverse-engineered Unity's VTA string array format through hex analysis
2. **Working Implementation** - Successfully patches UXML files and generates valid bundles
3. **Game-Tested** - Verified working in Football Manager without crashes
4. **Preserved Compression** - Output bundles maintain original 5.2MB size (not bloated to 40MB)

#### Technical Details

**Unity VTA String Array Format:**
```
count (4 bytes)
for each string:
    length (4 bytes)
    data (length bytes, NO null terminator)
padding to 4-byte boundary at end of array
```

**Individual string fields** (m_Type, m_Name) DO have null terminators.

**Files Modified:**
- `fm_skin_builder/core/uxml/uxml_element_parser.py` - Binary parser/serializer
- `fm_skin_builder/core/uxml/uxml_binary_patcher_v2.py` - In-place patcher
- `fm_skin_builder/core/uxml/uxml_importer.py` - Template separation fix

**Test Results:**
```
✅ PlayerAttributesCompactBlock - patched
✅ PlayerAttributesSmallBlock - patched
✅ PlayerAttributesStandardBlock - patched
✅ PlayerAttributesLargeBlock - patched

Bundle: test_output/ui-tiles_assets_all.bundle (5.2MB)
UnityPy: Successfully reads 2677 VisualTreeAssets
In-game: No crashes
```

### ⚠️ Limitations (Why Option B is Needed)

The in-place patcher **cannot** handle:

1. **Element Reordering** - Cannot change m_OrderInDocument
2. **Structural Changes** - Cannot change m_ParentId (parent-child relationships)
3. **Element Movement** - Cannot move elements to different positions in tree
4. **Binary Resizing** - Cannot expand/shrink elements beyond original size

**Example Use Case That Fails:**
- Swapping left/right footedness attributes requires moving elements
- This changes m_ParentId and m_OrderInDocument values
- In-place patcher explicitly skips these fields (lines 261-263 in uxml_binary_patcher_v2.py)

**Why These Are Skipped:**
```python
# IMPORTANT: Do NOT update m_OrderInDocument or m_ParentId from UXML
# These are internal VTA structure fields that should not be modified
# The UXML importer generates these incorrectly, so we ignore them
```

The comment is outdated (we fixed template separation), but the limitation remains:
**In-place patching cannot change element positions** because that would require:
- Changing byte offsets for every element after the moved one
- Rebuilding the entire VTA binary structure

---

## 🎯 Option B: Full Rebuild Approach

### Objective

Enable complete structural modifications including:
- ✅ Element reordering
- ✅ Parent-child relationship changes
- ✅ Element movement (e.g., footedness swap)
- ✅ Full UXML import/export round-trip

### Current Status

**Branch**: `claude/uxml-rebuild-full-structure` (NEW)

**Problem**: Rebuild approach currently produces bundles that crash the game

From uxml_binary_patcher_v2.py:83-86:
```python
# In-place patching failed (likely due to element growth)
# Rebuild method produces bundles that crash the game, so return None
log.error("In-place patching failed due to element growth - cannot patch this UXML")
```

### Known Issues to Investigate

1. **UnityPy Serialization Problems**
   - UnityPy's save() method may not serialize VTA correctly
   - Unknown if this is a UnityPy bug or usage issue

2. **Binary Structure Gaps**
   - We understand element binary format
   - May be missing VTA header structure
   - May be missing array boundary markers
   - May be missing TypeTree information

3. **Metadata Preservation**
   - Need to ensure all VTA metadata is preserved
   - UnknownObject handling may lose critical data
   - Field 4 (unknown_field_4) correlation not fully understood

### What We Know (Foundation for Option B)

#### ✅ Element Binary Structure (COMPLETE)

```
Offset  Size  Field
------  ----  -----
+0      4     m_Id
+4      4     m_OrderInDocument
+8      4     m_ParentId
+12     4     m_RuleIndex (0xFFFFFFFF for -1)
+16     4     m_PickingMode
+20     4     m_SkipClone
+24     4     m_XmlNamespace
+28     4     unknown_field_1
+32     4     unknown_field_2
+36     var   m_Classes (string array - no nulls between)
+?      var   m_StylesheetPaths (string array - no nulls between)
+?      4     unknown_field_3
+?      4     m_SerializedData (binding reference ID)
+?      4     unknown_field_4 (-1 for root, 0 for others?)
+?      4     unknown_field_5
+?      var   m_Type (string with null)
+?      var   m_Name (string with null, NOT aligned)
```

#### ✅ UXML Import/Export (WORKING)

- `uxml_exporter.py` - Exports VTA to UXML text ✅
- `uxml_importer.py` - Imports UXML to dict structure ✅
- Template separation fixed ✅
- Round-trip preserves most elements ✅

#### ❓ VTA Binary Structure (PARTIAL)

What we DON'T know yet:
- VTA header format (offsets 0-151)
- Array count field locations
- TypeTree structure
- Footer/padding requirements

### Approach for Option B

#### Phase 1: Understand VTA Header Structure

1. **Analyze VTA Header (offsets 0-151)**
   - Identify all count fields
   - Identify TypeTree references
   - Map all header fields to Unity documentation

2. **Study Working vs Broken Bundles**
   - Export original → reimport → compare hex
   - Identify what changes break the bundle
   - Find critical fields that must be preserved

#### Phase 2: Manual Binary Serialization

Instead of relying on UnityPy's save():

1. **Write VTA Binary Serializer**
   - Manually serialize VTA header
   - Serialize m_VisualElementAssets array
   - Serialize m_TemplateAssets array
   - Handle TypeTree correctly

2. **Preserve Unknown Fields**
   - Copy all unknown header bytes from original
   - Preserve unknown element fields
   - Match original padding/alignment

#### Phase 3: Test & Verify

1. **Round-trip Test**
   ```
   Original Bundle → Export UXML → Modify UXML → Rebuild Binary → Load in Game
   ```

2. **Progressive Testing**
   - Start with no modifications (pure round-trip)
   - Add simple class changes
   - Add element reordering
   - Add structural changes (footedness swap)

### Files to Study

**For VTA Header Understanding:**
- Original bundles in `test_bundles/`
- Analysis scripts in repo root (analyze_*.py)
- UnityPy source code for VTA handling

**For Manual Serialization:**
- `fm_skin_builder/core/uxml/uxml_element_parser.py` (element binary format - DONE)
- Create new: `fm_skin_builder/core/uxml/vta_serializer.py` (VTA binary builder)

**For Rebuild Implementation:**
- `fm_skin_builder/core/uxml/uxml_binary_patcher_v2.py` (add rebuild method)
- May need to bypass UnityPy entirely for VTA save

### Success Criteria

- ✅ Export UXML from bundle
- ✅ Modify UXML structurally (move elements)
- ✅ Rebuild VTA binary from modified UXML
- ✅ Bundle loads in UnityPy without errors
- ✅ Bundle works in Football Manager without crashes
- ✅ Structural changes (e.g., footedness swap) appear in-game

### Resources

**Unity Documentation:**
- VisualTreeAsset class reference
- UI Toolkit serialization format
- TypeTree specification

**Existing Code:**
- UnityPy VTA reading logic
- Our working element parser (uxml_element_parser.py)
- Our working UXML importer (uxml_importer.py)

**Test Data:**
- `test_bundles/ui-tiles_assets_all.bundle` (5.1MB original)
- `skins/new_skin/panels/*.uxml` (modified UXML with footedness swap)

---

## Decision Log

### 2025-11-16: Commit Option A, Start Option B

**Decision**: Preserve working in-place patcher, pursue full rebuild separately

**Rationale**:
- In-place patcher is valuable for CSS-only modifications
- Full rebuild is needed for structural changes
- Risk isolation: don't break working code while developing new approach
- Can fall back to Option A if Option B proves too difficult

**Actions**:
- ✅ Committed working in-place patcher to `claude/uxml-import-export-pipeline-011F7NNuAubpKgmoqPW6SgF2`
- ✅ Created new branch `claude/uxml-rebuild-full-structure`
- ✅ Documented current state and roadmap (this file)

### 2025-11-16: Discovered Unity String Array Format

**Decision**: String arrays have no null terminators between strings

**Evidence**:
- Hex analysis of element at offset 1660
- Manual parsing confirmed: count + [length + data]* + padding
- Individual fields (m_Type, m_Name) DO have nulls

**Impact**:
- Fixed parser in uxml_element_parser.py:238-263
- Fixed serializer in uxml_element_parser.py:111-133
- Fixed patcher in uxml_binary_patcher_v2.py:223-244
- Result: In-place patching now works!

### 2025-11-16: Fixed Template Separation

**Decision**: TemplateContainer elements must go into m_TemplateAssets array

**Problem**:
- Original: 44 visual + 9 template = 53 total
- Broken import: 52 visual + 0 template = 52 total
- All templates were being added to m_VisualElementAssets

**Fix**:
- Modified uxml_importer.py:126-194
- `_build_element_assets_from_xml()` now returns tuple
- Detects `elem.tag == 'TemplateContainer'`
- Separates into correct arrays

**Impact**:
- UXML import now preserves VTA structure correctly
- Element counts match original
- Prerequisite for full rebuild approach

---

## Quick Reference

### Run In-Place Patcher (Option A)
```bash
source .venv/bin/activate
python -m fm_skin_builder.cli.main patch skins/new_skin \
    --bundle test_bundles/ui-tiles_assets_all.bundle \
    --out test_output
```

### Export UXML for Analysis
```bash
source .venv/bin/activate
python -m fm_skin_builder.cli.main export-uxml \
    test_bundles/ui-tiles_assets_all.bundle \
    --asset-name PlayerAttributesLargeBlock \
    --output /tmp/exported.uxml
```

### Test Bundle in UnityPy
```bash
source .venv/bin/activate
python3 -c "
import UnityPy
env = UnityPy.load('test_output/ui-tiles_assets_all.bundle')
print(f'Loaded {len(list(env.objects))} objects')
"
```

---

## Next Steps (Priority Order)

1. **Analyze VTA Header** - Understand offsets 0-151 in binary
2. **Compare Working vs Broken** - See what UnityPy's save() breaks
3. **Write VTA Serializer** - Manual binary builder for VTA
4. **Test Round-Trip** - Pure export→import with no changes
5. **Add Structural Changes** - Enable element movement
6. **Verify In-Game** - Test footedness swap actually works

---

*This document will be updated as Option B progresses.*
