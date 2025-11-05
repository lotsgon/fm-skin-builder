# FM Skin Builder - UXML Import/Export Roadmap

## Project Overview

Transform FM Skin Builder from a **read-only explorer** into a **full round-trip skin editor** that can:
- Export UXML/USS to human-readable formats
- Allow modifications in standard text editors
- Re-import changes back into Unity bundles
- Preserve all bindings and references automatically

---

## Phase 1: UXML Re-Import Foundation (PRIORITY)

### ✅ 1.1 Clean UXML Export Format [COMPLETE]

**Goal**: Minimal, readable XML without excessive comments

**Implementation Status**: ✅ **COMPLETE**

**Implemented Features**:

1. ✅ **Three Export Modes** (`ExportMode` enum):
   - `MINIMAL` - Clean XML, no comments, data in attributes (default)
   - `STANDARD` - Some comments, balanced for reference
   - `VERBOSE` - Full details, all comments, debugging info

2. ✅ **CLI Integration**:
   ```bash
   python scripts/build_css_uxml_catalog.py \
     --bundle bundles/ui-tiles_assets_all.bundle \
     --export-files \
     --export-mode minimal  # or standard, verbose
   ```

3. ✅ **Binding Attributes** (MINIMAL mode):
   ```xml
   <BindingRemapper
       data-unity-id="-1320750867"
       data-binding-rid="1000"
       data-binding-mappings="person -&gt; binding;player -&gt; binding">
   ```

4. ✅ **Mode-Aware Comment Generation**:
   - Template comments: STANDARD/VERBOSE only
   - Binding header: STANDARD/VERBOSE with detail level control
   - Inline comments: STANDARD (first 3), VERBOSE (all)
   - Component type comments: STANDARD/VERBOSE only

**Attribute Schema** (as implemented):
```xml
<!-- Core attributes -->
data-unity-id="{m_Id}"                          <!-- Element ID -->

<!-- Binding attributes (MINIMAL mode only) -->
data-binding-rid="{rid}"                        <!-- Reference ID -->
data-binding-textbinding="{path}"               <!-- TextBinding -->
data-binding-mappings="{from->to;...}"          <!-- Mappings -->
data-binding-parameters="{param1;param2}"       <!-- Parameters -->
data-binding-valuevariables="{var1;var2}"       <!-- Variables -->
data-binding-hoverbinding="{path}"              <!-- Hover binding -->
data-binding-binding="{path}"                   <!-- Generic binding -->
```

**File Size Impact** (measured on PlayerAttributesTile.uxml):
- MINIMAL: 132 lines, 8.1 KB (100% baseline)
- STANDARD: ~10-12 KB (~125-150%)
- VERBOSE: ~15-20 KB (~190-250%)

**Files Modified**:
- `src/utils/uxml_parser.py` - Added ExportMode enum, mode-aware XML generation
- `scripts/build_css_uxml_catalog.py` - CLI argument, mode threading

**Documentation**:
- See [docs/EXPORT_MODES.md](EXPORT_MODES.md) for complete usage guide

---

### 1.2 UXML Parser (XML → Unity Structure)

**Goal**: Parse modified UXML back into Unity's VisualTreeAsset structure

**Components**:

1. **XML Parser** (`src/utils/uxml_importer.py`):
   ```python
   class UXMLImporter:
       def parse_uxml_file(self, xml_path: str) -> VisualTreeAsset:
           """Parse UXML XML back to Unity structure"""

       def build_element_assets(self, xml_tree) -> List[VisualElementAsset]:
           """Convert XML elements to m_VisualElementAssets"""

       def build_managed_references(self, xml_tree, elements) -> ManagedReferencesRegistry:
           """Rebuild bindings from unity:binding-* attributes"""

       def validate_bindings(self, bindings, elements) -> List[ValidationError]:
           """Check all uxmlAssetIds match element m_Ids"""
   ```

2. **Element ID Management**:
   - **Preserve existing IDs** from `unity:id` attribute
   - **Generate new IDs** for new elements (hash-based, Unity-compatible)
   - **Collision detection** - ensure no duplicate IDs
   - **ID mapping** - track old→new for binding updates

3. **Binding Reconstruction**:
   ```python
   def parse_binding_attributes(self, element_xml) -> Dict:
       """
       Extract binding data from unity:binding-* attributes
       Returns binding configuration for ManagedReferencesRegistry
       """
       binding_data = {}

       if element_xml.get('unity:binding-text'):
           binding_data['TextBinding'] = {
               'm_kind': 2,
               'm_direct': {'m_path': element_xml.get('unity:binding-text')}
           }

       if element_xml.get('unity:binding-mappings'):
           mappings = []
           for mapping in element_xml.get('unity:binding-mappings').split(';'):
               from_val, to_val = mapping.split('->')
               mappings.append({
                   'from_': from_val.strip(),
                   'to': {'m_path': to_val.strip()}
               })
           binding_data['Mappings'] = mappings

       return binding_data
   ```

4. **Validation System**:
   - ✅ All `unity:id` values are unique
   - ✅ All binding RIDs are unique
   - ✅ All binding `uxmlAssetId` values match an element
   - ✅ Element types match binding types
   - ✅ Template references exist
   - ⚠️ Warn on missing stylesheets
   - ⚠️ Warn on unknown CSS classes

---

### 1.3 Bundle Writer (Unity Structure → Bundle File)

**Goal**: Write modified VisualTreeAsset back into Unity bundle

**Approach**: Use UnityPy's serialization capabilities

**Components**:

1. **Bundle Modifier** (`src/utils/bundle_writer.py`):
   ```python
   class BundleWriter:
       def __init__(self, bundle_path: str):
           self.env = UnityPy.load(bundle_path)

       def update_visual_tree_asset(self, asset_name: str, new_data: VisualTreeAsset):
           """Replace VisualTreeAsset in bundle"""

       def save_bundle(self, output_path: str):
           """Write modified bundle to disk"""
   ```

2. **UnityPy Serialization**:
   ```python
   # Find the MonoBehaviour object
   for obj in env.objects:
       if obj.type.name == 'MonoBehaviour':
           data = obj.read()
           if data.m_Name == asset_name:
               # Update the data
               data.m_VisualElementAssets = new_elements
               data.references = new_managed_references

               # Write back
               obj.save()

   # Save bundle
   with open(output_path, 'wb') as f:
       f.write(env.file.save())
   ```

3. **Testing Strategy**:
   - Extract UXML from bundle
   - Make NO changes
   - Re-import to bundle
   - Export again
   - Binary diff should show minimal differences (timestamps only)

**Challenges**:
- UnityPy serialization might not preserve exact binary format
- Unity might reject modified bundles (signature checks)
- Need to test with actual FM installation

---

## Phase 2: CSS/USS Management (MEDIUM PRIORITY)

### 2.1 USS Export Enhancement

**Current State**: USS files exported as-is with path IDs

**Goal**: Human-readable USS with automatic reference management

**Implementation**:

1. **USS Path Registry** (`extracted_sprites/uss_registry.json`):
   ```json
   {
     "ui-styles_assets_common.bundle": {
       "path_id": 123456,
       "virtual_path": "Assets/UI/Styles/common.uss",
       "classes": [".button", ".heading"],
       "variables": ["--color-primary"],
       "used_by_uxml": ["MainMenu", "PlayerCard"]
     }
   }
   ```

2. **Automatic USS Detection**:
   ```python
   def detect_required_stylesheets(self, uxml_data: UXMLDocument) -> List[str]:
       """
       Analyze UXML classes and variables to determine which USS files are needed
       """
       required_uss = set()

       for css_class in uxml_data.classes_used:
           # Look up which USS files define this class
           uss_files = self.uss_registry.find_stylesheets_with_class(css_class)
           required_uss.update(uss_files)

       return sorted(required_uss)
   ```

3. **USS Reference in UXML**:
   ```xml
   <ui:UXML xmlns:ui="UnityEngine.UIElements">
       <Style src="common.uss" unity:path-id="123456" />
       <Style src="buttons.uss" unity:path-id="789012" />
   ```

4. **Missing USS Warning**:
   ```
   ⚠️  Warning: UXML uses classes not found in linked stylesheets:
       .custom-button (not found in any USS)
       .new-heading (not found in any USS)

   Suggestion: Add these classes to common.uss or create new stylesheet
   ```

---

### 2.2 New USS File Creation

**Goal**: Add custom USS files to existing bundles

**Approach**: Inject new TextAsset into bundle with unused PathID

1. **PathID Allocation**:
   ```python
   def find_unused_path_id(self, bundle: UnityPy.Environment) -> int:
       """Find next available PathID in bundle"""
       used_ids = set()
       for obj in bundle.objects:
           used_ids.add(obj.path_id)

       # Start from high number to avoid conflicts
       new_id = 1000000
       while new_id in used_ids:
           new_id += 1

       return new_id
   ```

2. **USS TextAsset Creation**:
   ```python
   def create_uss_asset(self, uss_content: str, virtual_path: str) -> TextAsset:
       """Create new Unity TextAsset for USS"""
       asset = TextAsset()
       asset.m_Name = Path(virtual_path).stem
       asset.m_Script = uss_content.encode('utf-8')
       return asset
   ```

3. **Bundle Injection**:
   ```python
   def inject_uss_into_bundle(self, bundle_path: str, uss_path: str, uss_content: str):
       """Add new USS file to bundle"""
       env = UnityPy.load(bundle_path)

       # Create TextAsset
       new_path_id = self.find_unused_path_id(env)
       text_asset = self.create_uss_asset(uss_content, uss_path)

       # Add to bundle
       env.add_object(text_asset, path_id=new_path_id)

       # Update registry
       self.uss_registry.register(uss_path, new_path_id, bundle_path)

       # Save
       env.save(bundle_path + '.modified')
   ```

**Limitations**:
- Unity might not recognize new assets without CAB metadata
- May require modifying bundle's asset list/TOC
- Might only work with loose bundles (not encrypted/compressed)

**Alternative Approach** (if injection fails):
- Keep custom USS in separate folder: `skins/custom/styles/`
- Reference via relative paths in UXML
- FM engine might support external USS loading

---

### 2.3 Inline Styles Preservation

**Current**: Detected but not exported in detail

**Goal**: Full inline style round-trip

**Implementation**:

1. **Style Parsing** (already exists in Unity):
   ```python
   def export_inline_styles(self, element: VisualElementAsset) -> str:
       """Convert m_Properties to CSS string"""
       properties = element.m_Properties
       style_parts = []

       for prop in properties:
           # Unity stores properties in some format
           # Need to reverse-engineer property structure
           style_parts.append(f"{prop.name}: {prop.value}")

       return "; ".join(style_parts)
   ```

2. **UXML Export**:
   ```xml
   <VisualElement
       style="width: 100px; height: 50px; background-color: #FF0000;"
       unity:id="123456">
   ```

3. **UXML Import**:
   ```python
   def parse_inline_styles(self, style_string: str) -> List[PropertyValue]:
       """Convert CSS string to Unity properties"""
       properties = []
       for declaration in style_string.split(';'):
           if ':' in declaration:
               prop, value = declaration.split(':', 1)
               properties.append({
                   'name': prop.strip(),
                   'value': value.strip()
               })
       return properties
   ```

---

## Phase 3: Font Management (MEDIUM PRIORITY)

### 3.1 Font Detection and Export

**Goal**: Extract font references and data from bundles

**Implementation**:

1. **Font Asset Scanner**:
   ```python
   def scan_font_assets(self, bundle_dir: Path) -> Dict[str, FontAsset]:
       """Find all font assets in bundles"""
       fonts = {}

       for bundle_path in bundle_dir.glob('*.bundle'):
           env = UnityPy.load(str(bundle_path))

           for obj in env.objects:
               if obj.type.name == 'Font':
                   font_data = obj.read()
                   fonts[font_data.m_Name] = {
                       'bundle': bundle_path.name,
                       'path_id': obj.path_id,
                       'font_size': font_data.m_FontSize,
                       'type': 'TrueType' or 'SDF'  # Detect type
                   }

       return fonts
   ```

2. **Font Reference in UXML**:
   ```xml
   <SIText
       unity:font="Arial-Bold"
       unity:font-id="234567"
       class="heading">
   ```

3. **Font Export** (if possible):
   ```python
   def export_font(self, font_asset, output_path: Path):
       """Extract font file from bundle"""
       # For TrueType: Extract .ttf
       # For SDF: Extract atlas texture + metadata
   ```

---

### 3.2 Font Replacement

**Goal**: Replace existing fonts with custom ones

**Approach**:

1. **Override Existing Font**:
   ```python
   def replace_font(self, bundle_path: str, font_name: str, new_font_path: str):
       """Replace font asset in bundle"""
       env = UnityPy.load(bundle_path)

       # Find font object
       for obj in env.objects:
           if obj.type.name == 'Font':
               font_data = obj.read()
               if font_data.m_Name == font_name:
                   # Load new font
                   with open(new_font_path, 'rb') as f:
                       font_data.m_FontData = f.read()

                   obj.save()
                   break

       env.save(bundle_path + '.modified')
   ```

**Challenges**:
- SDF fonts require atlas generation (complex)
- Font metrics must match original
- Unity might validate font format

**Recommendation**: Start with TrueType, add SDF later

---

## Phase 4: Static Data Editing (LOW PRIORITY)

### 4.1 Data Type Detection

**Goal**: Find and export editable game data

**Implementation**:

1. **Data Scanner**:
   ```python
   def scan_static_data(self, bundle_dir: Path) -> Dict[str, Any]:
       """Find arrays of game data (colors, backgrounds, etc.)"""
       data_assets = {}

       for bundle_path in bundle_dir.glob('*.bundle'):
           env = UnityPy.load(str(bundle_path))

           for obj in env.objects:
               if obj.type.name == 'MonoBehaviour':
                   data = obj.read()

                   # Look for known data types
                   if hasattr(data, 'AttributeColors'):
                       data_assets['attribute_colors'] = data.AttributeColors

                   if hasattr(data, 'BackgroundList'):
                       data_assets['backgrounds'] = data.BackgroundList

       return data_assets
   ```

2. **JSON Export**:
   ```json
   {
     "attribute_colors": [
       {"attribute": "Passing", "min": "#FF0000", "max": "#00FF00"},
       {"attribute": "Shooting", "min": "#FF0000", "max": "#00FF00"}
     ],
     "backgrounds": [
       {"id": 0, "name": "Premier League", "texture_path": "..."},
       {"id": 1, "name": "La Liga", "texture_path": "..."}
     ]
   }
   ```

3. **Modification & Re-import**:
   ```python
   def update_static_data(self, bundle_path: str, data_type: str, new_data: Any):
       """Update game data in bundle"""
   ```

---

## Phase 5: Asset Addition (ADVANCED - LOW PRIORITY)

### 5.1 New Background Addition

**Goal**: Add new competition backgrounds without overriding existing

**Challenges**:
- Requires expanding arrays in game data
- Might need code changes in DLLs (impossible)
- Background IDs might be hardcoded

**Feasibility**: ⚠️ **LOW** - Likely requires game code changes

**Alternative**:
- Override existing backgrounds that aren't used
- Provide tool to identify least-used backgrounds

---

### 5.2 New Font Addition

**Similar challenges to backgrounds**

**Alternative**:
- Override existing fonts
- Provide usage stats to help choose which font to replace

---

## Implementation Phases Summary

### Phase 1: Core Round-Trip (WEEKS 1-3)
- ✅ Clean UXML export (minimal mode)
- ✅ UXML parser (XML → Unity)
- ✅ Bundle writer (Unity → Bundle)
- ✅ Basic validation
- ✅ Integration tests

**Deliverable**: Can export→modify→import UXML with preserved bindings

### Phase 2: CSS Management (WEEKS 4-5)
- ✅ USS registry system
- ✅ Automatic USS detection
- ✅ Inline styles round-trip
- ⚠️ New USS injection (if possible)

**Deliverable**: Full CSS/USS management with smart references

### Phase 3: Font Support (WEEK 6)
- ✅ Font detection and registry
- ✅ Font replacement (TrueType)
- ⚠️ SDF font support (if possible)

**Deliverable**: Can replace fonts in skins

### Phase 4: Static Data (WEEK 7)
- ✅ Data detection and export
- ✅ JSON editing interface
- ✅ Data import

**Deliverable**: Can edit colors, credits, static data

### Phase 5: Advanced Features (WEEK 8+)
- ⚠️ New asset addition (research required)
- ✅ Advanced validation
- ✅ Skin packaging system

---

## Technical Risks & Mitigations

### Risk 1: UnityPy Serialization
**Risk**: UnityPy might not serialize bundles correctly
**Mitigation**:
- Test extensively with read→write→read cycles
- Compare binary diffs
- Fall back to hex editing if needed

### Risk 2: FM Bundle Validation
**Risk**: FM might reject modified bundles
**Mitigation**:
- Preserve as much original structure as possible
- Test with actual FM installation early
- Research FM's bundle loading code

### Risk 3: USS Injection
**Risk**: Unity might not recognize injected assets
**Mitigation**:
- Research CAB format and asset lists
- Test with Unity Editor if available
- Fall back to external USS files

### Risk 4: Element ID Conflicts
**Risk**: Generated IDs might collide with existing ones
**Mitigation**:
- Use Unity's hash algorithm
- Validate all IDs are unique
- Provide ID remapping tool

---

## Testing Strategy

### Unit Tests
```python
# Test UXML parsing
def test_parse_minimal_uxml():
    xml = '<VisualElement unity:id="123" class="button" />'
    result = UXMLImporter().parse(xml)
    assert result.elements[0].m_Id == 123

# Test binding reconstruction
def test_rebuild_text_binding():
    xml = '<SIText unity:binding-text="Player.Name" />'
    result = UXMLImporter().parse(xml)
    assert result.bindings[0].TextBinding.m_path == "Player.Name"
```

### Integration Tests
```python
# Test full round-trip
def test_roundtrip_uxml():
    # Export
    original = export_uxml_from_bundle('test.bundle', 'TestFile')

    # Import
    reimport_uxml_to_bundle('test.bundle', 'TestFile', original)

    # Export again
    result = export_uxml_from_bundle('test.bundle', 'TestFile')

    # Compare (should be identical)
    assert original == result
```

### Manual Tests
1. Export PlayerCard UXML
2. Change text element class
3. Re-import to bundle
4. Load in FM
5. Verify changes appear in-game

---

## File Structure

```
fm-skin-builder/
├── src/
│   ├── utils/
│   │   ├── uxml_exporter.py      # Enhanced with modes
│   │   ├── uxml_importer.py      # NEW - XML to Unity
│   │   ├── bundle_writer.py      # NEW - Write bundles
│   │   ├── uss_manager.py        # NEW - USS registry
│   │   └── font_manager.py       # NEW - Font handling
│   └── validators/
│       ├── binding_validator.py  # NEW - Validate bindings
│       └── element_validator.py  # NEW - Validate elements
├── scripts/
│   ├── export_skin.py            # ENHANCED - Export with modes
│   ├── import_skin.py            # NEW - Import modified skin
│   ├── validate_skin.py          # NEW - Validate before import
│   └── package_skin.py           # NEW - Package for distribution
└── docs/
    ├── IMPORT_EXPORT_GUIDE.md    # NEW - User guide
    ├── TECHNICAL_SPEC.md         # NEW - Technical details
    └── TROUBLESHOOTING.md        # NEW - Common issues
```

---

## CLI Commands

```bash
# Export with minimal format
python scripts/export_skin.py --mode minimal --output my_skin/

# Export with verbose comments
python scripts/export_skin.py --mode verbose --output my_skin_debug/

# Validate before import
python scripts/validate_skin.py --input my_skin/

# Import skin
python scripts/import_skin.py --input my_skin/ --bundles bundles/

# Package skin for distribution
python scripts/package_skin.py --input my_skin/ --output my_skin_v1.0.zip
```

---

## Questions to Answer Before Starting

1. **UnityPy Capabilities**:
   - Can UnityPy serialize ManagedReferencesRegistry?
   - Can it write modified bundles?
   - Test: Simple write→read cycle

2. **FM Bundle Format**:
   - Does FM validate bundle signatures?
   - Can we inject new assets?
   - Test: Load modified bundle in FM

3. **Element ID Generation**:
   - What's Unity's hash algorithm for m_Id?
   - How deterministic is it?
   - Test: Create element in Unity, check ID

4. **USS Loading**:
   - Does FM support external USS?
   - Can we use relative paths?
   - Test: Reference external USS in UXML

---

## Success Criteria

**Phase 1 Success**:
- ✅ Export UXML to clean, readable XML
- ✅ Modify layout (add/remove/reorder elements)
- ✅ Re-import to bundle
- ✅ Load in FM - changes appear correctly
- ✅ All bindings still work

**Phase 2 Success**:
- ✅ USS files linked correctly
- ✅ Can add custom USS (or understand why not)
- ✅ Inline styles preserved

**Full Project Success**:
- ✅ Complete round-trip editing workflow
- ✅ Minimal file sizes
- ✅ Comprehensive validation
- ✅ User-friendly tools
- ✅ Clear documentation

---

## Next Steps

1. **Research Phase** (1-2 days):
   - Test UnityPy serialization capabilities
   - Test modified bundle loading in FM
   - Document findings

2. **Prototype** (2-3 days):
   - Simple UXML export→import→export cycle
   - Verify binary preservation
   - Test with one simple UXML file

3. **Implementation** (follow phases above)

4. **Documentation** (throughout):
   - Technical specs
   - User guides
   - API documentation

---

## Conclusion

This is an ambitious project that will transform FM Skin Builder into a complete skin editing suite. The core round-trip functionality (Phase 1) is achievable with moderate effort. Advanced features (USS injection, new assets) may hit Unity/FM limitations, but we can provide good alternatives.

**Recommended Start**: Focus on Phase 1 (UXML round-trip) with minimal export mode. Once that works reliably, expand to other features.

**Timeline Estimate**: 6-8 weeks for Phases 1-3, with Phases 4-5 as stretch goals depending on technical feasibility.
