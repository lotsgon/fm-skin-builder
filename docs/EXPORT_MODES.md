# UXML Export Modes

The UXML exporter supports three modes to suit different use cases:

## 📊 Mode Comparison

| Feature | MINIMAL | STANDARD | VERBOSE |
|---------|---------|----------|---------|
| **Primary Use** | Editing & Re-import | Reference & Documentation | Deep Debugging |
| **File Size** | Smallest | Medium | Largest |
| **Comments** | None | Some | All |
| **Binding Data Location** | XML Attributes | Comments | Comments |
| **Template Comments** | ❌ No | ✅ Yes | ✅ Yes |
| **Binding Header** | ❌ No | ✅ Yes (compact) | ✅ Yes (detailed) |
| **Inline Comments** | ❌ No | ✅ Limited (first 3) | ✅ All |
| **Component Type Comments** | ❌ No | ✅ Yes | ✅ Yes |

## 🎯 MINIMAL Mode

**Purpose**: Clean, human-editable XML for modification and re-import

**Characteristics**:
- No comments of any kind
- Binding data stored in XML attributes (`data-binding-*`)
- Smallest file size
- Easy to parse and modify
- Default mode for exports

**Attribute Schema**:
```xml
<Element
    data-unity-id="{m_Id}"
    data-binding-rid="{rid}"
    data-binding-{key}="{value}">
```

**Example**:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <UXML data-unity-id="382705796">
        <BindingRemapper data-unity-id="-1320750867"
                         data-binding-rid="1000"
                         data-binding-mappings="person -&gt; binding;player -&gt; binding">
            <VisualElement data-unity-id="-250374529">
                <BindingExpect class="flex-grow-class"
                               data-unity-id="-701132486"
                               data-binding-rid="1002"
                               data-binding-parameters="isonmainscreen">
                    <!-- Clean, readable XML -->
                </BindingExpect>
            </VisualElement>
        </BindingRemapper>
    </UXML>
</ui:UXML>
```

**When to use**:
- ✅ Editing UXML files manually
- ✅ Version control (cleaner diffs)
- ✅ Preparing files for re-import
- ✅ Reducing file size

## 📖 STANDARD Mode

**Purpose**: Balanced view with helpful context for understanding

**Characteristics**:
- Template usage comments at the top
- Compact binding header (max 50 bindings)
- Component type comments for custom components
- Inline binding comments (first 3 key-value pairs)
- Binding data in comments (not attributes)

**Example**:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <!-- UXML Templates Used In This File -->
    <!-- Template: states-templates-tile-content class="states-templates-tile-content" -->

    <!-- ============================================ -->
    <!-- DATA BINDINGS (connects UI to game data)   -->
    <!-- ============================================ -->

    <!-- UxmlSerializedData[rid=1000] -->
    <!-- UxmlSerializedData[rid=1002, name="TileBindingExpect"] -->
    <!-- UxmlSerializedData[rid=1004, name="TileVariables"] -->

    <UXML data-unity-id="382705796">
        <!-- SI.Bindable.BindingRemapper -->
        <!-- BINDING[rid=1000]: Mappings: person -> binding; Mappings: player -> binding -->
        <BindingRemapper data-unity-id="-1320750867">
            <VisualElement data-unity-id="-250374529">
                <!-- SI.Bindable.BindingExpect -->
                <!-- BINDING[rid=1002]: Parameters: isonmainscreen -->
                <BindingExpect class="flex-grow-class" data-unity-id="-701132486">
                    <!-- More elements... -->
                </BindingExpect>
            </VisualElement>
        </BindingRemapper>
    </UXML>
</ui:UXML>
```

**When to use**:
- ✅ Understanding file structure
- ✅ Learning the binding system
- ✅ Quick reference during development
- ✅ Initial exploration of assets

## 🔍 VERBOSE Mode

**Purpose**: Maximum detail for debugging and analysis

**Characteristics**:
- All template comments
- Full binding header with detailed breakdown per binding
- All component type comments
- All inline binding comments (no limit)
- Shows "... and N more bindings" for large sets

**Example**:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <!-- UXML Templates Used In This File -->
    <!-- Template: states-templates-tile-content class="states-templates-tile-content" -->

    <!-- ============================================ -->
    <!-- DATA BINDINGS (connects UI to game data)   -->
    <!-- Format: BindingType[rid=ID, name="..."]     -->
    <!--   key: value                               -->
    <!-- ============================================ -->

    <!-- UxmlSerializedData[rid=1000] -->
    <!--   Mappings: -->
    <!--     - person -&gt; binding -->
    <!--     - player -&gt; binding -->
    <!--  -->
    <!-- UxmlSerializedData[rid=1002, name="TileBindingExpect"] -->
    <!--   Parameters: -->
    <!--     - isonmainscreen -->
    <!--  -->

    <UXML data-unity-id="382705796">
        <!-- SI.Bindable.BindingRemapper -->
        <!-- BINDING[rid=1000]: Mappings: person -> binding; Mappings: player -> binding -->
        <BindingRemapper data-unity-id="-1320750867">
            <!-- Full details for every element... -->
        </BindingRemapper>
    </UXML>
</ui:UXML>
```

**When to use**:
- ✅ Debugging binding issues
- ✅ Analyzing complex UXML files
- ✅ Documentation generation
- ✅ Understanding Unity's internal structure

## 🛠️ Usage

### Command Line

```bash
# MINIMAL mode (default)
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-tiles_assets_all.bundle \
  --output catalog.json \
  --export-files \
  --export-mode minimal

# STANDARD mode
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-tiles_assets_all.bundle \
  --output catalog.json \
  --export-files \
  --export-mode standard

# VERBOSE mode
python scripts/build_css_uxml_catalog.py \
  --bundle bundles/ui-tiles_assets_all.bundle \
  --output catalog.json \
  --export-files \
  --export-mode verbose
```

### Python API

```python
from src.utils.uxml_parser import visual_tree_asset_to_xml, ExportMode

# MINIMAL mode
xml = visual_tree_asset_to_xml(data, name, ExportMode.MINIMAL)

# STANDARD mode
xml = visual_tree_asset_to_xml(data, name, ExportMode.STANDARD)

# VERBOSE mode
xml = visual_tree_asset_to_xml(data, name, ExportMode.VERBOSE)
```

## 📐 Binding Attribute Format (MINIMAL Mode Only)

When using MINIMAL mode, binding data is stored in XML attributes following this schema:

### Core Attributes

- `data-unity-id`: Unity's internal element ID (always present)
- `data-binding-rid`: Reference ID to the binding data in Unity's system

### Binding Attributes

Each binding property becomes an attribute with the pattern:
- `data-binding-{key}` where `{key}` is the property name in lowercase with underscores replaced by hyphens

**Examples**:

```xml
<!-- TextBinding property -->
data-binding-textbinding="Person.Name"

<!-- Parameters list -->
data-binding-parameters="isonmainscreen"

<!-- ValueVariables list -->
data-binding-valuevariables="TileInteraction"

<!-- Mappings with arrow notation -->
data-binding-mappings="person -&gt; binding;player -&gt; binding"

<!-- Complex binding path -->
data-binding-binding="Person.IsGoalkeeper"

<!-- Hover binding -->
data-binding-hoverbinding="TileInteraction"
```

### Attribute Value Escaping

- XML special characters are escaped (`&`, `<`, `>`, `"`, `'`)
- Semicolons separate multiple values in list properties
- Arrow notation (`->`) used for mapping relationships
- Values truncated to 200 characters max with `...` suffix

### Re-import Support

The attribute format is designed for round-trip compatibility:
1. Export to MINIMAL mode
2. Edit XML attributes
3. Parse attributes back to binding data
4. Write to Unity bundle

This enables the full editing workflow described in the roadmap.

## 🎓 Best Practices

1. **For Daily Work**: Use MINIMAL mode
   - Cleaner files for version control
   - Easier to read and edit
   - Smaller diffs in Git

2. **For Documentation**: Use STANDARD mode
   - Good balance of detail and readability
   - Helps understand structure
   - Not overwhelming

3. **For Debugging**: Use VERBOSE mode
   - All information preserved
   - No detail lost
   - Easier to spot issues

4. **For Team Sharing**: Use STANDARD or VERBOSE
   - More self-documenting
   - Easier for others to understand
   - Better onboarding

## 🔄 Migration Path

When transitioning from old exports to new system:

1. **Review existing exports** (currently STANDARD-like)
2. **Switch to MINIMAL** for ongoing work
3. **Keep VERBOSE exports** for reference documentation
4. **Update build scripts** to use appropriate modes

## 📏 File Size Impact

Based on `PlayerAttributesTile.uxml` (132 lines):

- **MINIMAL**: ~8 KB (100% baseline)
- **STANDARD**: ~10-12 KB (~125-150%)
- **VERBOSE**: ~15-20 KB (~190-250%)

Larger files show even more dramatic differences. On a 2,681-file export, MINIMAL mode can save **30-50% disk space** compared to VERBOSE.

## 🚀 Future Enhancements

- [ ] Add `--smart` mode that chooses based on file complexity
- [ ] Support per-file mode configuration
- [ ] Add validation mode that checks binding integrity
- [ ] Create diff tool that understands binding attributes
- [ ] Add mode conversion tool (MINIMAL ↔ STANDARD ↔ VERBOSE)
