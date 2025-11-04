# UXML Binding XML Format Specification

## Overview

Binding data is exported in UXML files as **structured XML comments** that can be parsed back to rebuild the Unity `ManagedReferencesRegistry` during import.

## Format Version

**Version**: 1.0
**Unity Version**: 2022.3+
**FM Version**: 2025

## XML Comment Structure

### Header Section

Located after templates, before the main UXML body:

```xml
<!-- ============================================ -->
<!-- DATA BINDINGS (connects UI to game data)   -->
<!-- Format: BindingType[rid=ID, name="..."]     -->
<!--   key: value                               -->
<!-- ============================================ -->

<!-- UxmlSerializedData[rid=1000] -->
<!--   Mappings: -->
<!--     - person -> binding -->
<!--     - player -> binding -->
<!--  -->
<!-- UxmlSerializedData[rid=1002, name="TileBindingExpect"] -->
<!--   Parameters: -->
<!--     - isonmainscreen -->
<!--  -->
```

### Inline Element Bindings

Located directly before the element they apply to:

```xml
<!-- SI.Bindable.SIText -->
<!-- BINDING[rid=1028]: TextBinding: Club.Background -->
<SIText name="club-name" class="body-small-12px-regular" />
```

## Binding Entry Format

### Header Binding Format

```
<!-- UxmlSerializedData[rid={RID}, name="{NAME}"] -->
<!--   {KEY}: {VALUE} -->
<!--   {KEY}: -->
<!--     - {LIST_ITEM_1} -->
<!--     - {LIST_ITEM_2} -->
<!--  -->
```

**Fields**:
- `{RID}`: Integer - Unity's Reference ID (e.g., `1000`, `1028`)
- `{NAME}`: String - Element name (optional, empty if unnamed)
- `{KEY}`: String - Binding property name (e.g., `TextBinding`, `Mappings`, `Parameters`)
- `{VALUE}`: String - Binding value (for simple properties)
- `{LIST_ITEM}`: String - List item (for array properties)

### Inline Binding Format

```
<!-- BINDING[rid={RID}]: {KEY}: {VALUE}; {KEY}: {VALUE}; ... -->
```

**Fields**:
- `{RID}`: Integer - Unity's Reference ID
- Multiple key-value pairs separated by semicolons
- Maximum 3 key-value pairs shown inline (rest in header)

## Binding Types and Properties

### 1. BindingRemapper

**Purpose**: Maps variable names to data paths

**Properties**:
- `Mappings`: Array of `"{from} -> {to}"` strings

**Example**:
```xml
<!-- UxmlSerializedData[rid=1052] -->
<!--   Mappings: -->
<!--     - team -> Club.MainTeam -->
<!--     - player -> Team.Players[0] -->
<!--  -->
```

**Inline**:
```xml
<!-- BINDING[rid=1052]: Mappings: team -> Club.MainTeam -->
<BindingRemapper>
```

### 2. BindingExpect

**Purpose**: Declares required input parameters

**Properties**:
- `Parameters`: Array of parameter name strings

**Example**:
```xml
<!-- UxmlSerializedData[rid=1000, name="TileBindingExpect"] -->
<!--   Parameters: -->
<!--     - club -->
<!--     - person -->
<!--     - isonmainscreen -->
<!--  -->
```

**Inline**:
```xml
<!-- BINDING[rid=1000]: Parameters: club -->
<BindingExpect name="TileBindingExpect">
```

### 3. BindingVariables

**Purpose**: Declares local variables

**Properties**:
- `ValueVariables`: Array of variable name strings

**Example**:
```xml
<!-- UxmlSerializedData[rid=1030] -->
<!--   ValueVariables: -->
<!--     - selectedtab -->
<!--     - viewid -->
<!--     - rolemask -->
<!--  -->
```

**Inline**:
```xml
<!-- BINDING[rid=1030]: ValueVariables: [3 items] -->
<BindingVariables>
```

### 4. Component Bindings

#### SIText

**Properties**:
- `TextBinding`: String - Data path to text value

**Example**:
```xml
<!-- UxmlSerializedData[rid=1028] -->
<!--   TextBinding: Club.Background -->
<!--  -->
```

**Inline**:
```xml
<!-- BINDING[rid=1028]: TextBinding: Club.Background -->
<SIText name="club-bg" />
```

#### SIVisible

**Properties**:
- `Binding`: String - Data path to boolean visibility value

**Example**:
```xml
<!-- BINDING[rid=1038]: Binding: Club.ReservesTeam -->
<SIVisible name="reserves-visible">
```

#### SIEnabled

**Properties**:
- `Binding`: String - Data path to boolean enabled value

**Example**:
```xml
<!-- BINDING[rid=1050]: Binding: Form.IsValid -->
<SIEnabled name="submit-enabled">
```

#### BindableSwitchElement

**Properties**:
- `Binding`: String - Data path to boolean switch value

**Example**:
```xml
<!-- BINDING[rid=1013]: Binding: Person.IsGoalkeeper -->
<BindableSwitchElement name="IsGoalkeeperSwitch">
```

#### SIButton

**Properties**:
- `HoverBinding`: String - Data path for hover state

**Example**:
```xml
<!-- BINDING[rid=1005]: HoverBinding: TileInteraction -->
<SIButton name="tile-button">
```

#### StreamedObjectList

**Properties**:
- `Binding`: String - Data path to list source
- `SelectedItemsBinding`: String - Data path for selection
- `SortBinding`: String - Data path for sorting
- `ScrollToElementBinding`: String - Data path for scroll target
- `ViewWindowBinding`: String - Data path for view window

**Example**:
```xml
<!-- UxmlSerializedData[rid=1019] -->
<!--   Binding: Team.Players -->
<!--   SelectedItemsBinding: selectedplayers -->
<!--   SortBinding: playersort -->
<!--  -->
```

## Escaping Rules

XML special characters are escaped in binding values:

- `&` → `&amp;`
- `<` → `&lt;`
- `>` → `&gt;`
- `"` → `&quot;` (in attribute values)
- `'` → `&apos;` (in attribute values)

**Example**:
```xml
<!-- Mappings: -->
<!--   - value -> Data.Value&lt;int&gt; -->
```

## Parsing Back to Unity Format

### Step 1: Extract Header Bindings

Parse comments matching pattern:
```regex
<!-- UxmlSerializedData\[rid=(\d+)(?:, name="([^"]*)")?\] -->
```

Capture groups:
1. RID (integer)
2. Name (optional string)

### Step 2: Extract Binding Properties

For each binding entry, parse properties:

**Simple property**:
```regex
<!--   (\w+): (.+) -->
```
Capture: key, value

**Array property header**:
```regex
<!--   (\w+): -->
```
Capture: key

**Array items**:
```regex
<!--     - (.+) -->
```
Capture: item value

### Step 3: Extract Inline Bindings

Parse inline bindings matching:
```regex
<!-- BINDING\[rid=(\d+)\]: (.+) -->
```

Capture groups:
1. RID (integer)
2. Key-value pairs (semicolon-separated)

Split key-value pairs:
```regex
(\w+): ([^;]+)
```

### Step 4: Match to Elements

**Method 1: By uxmlAssetId**
- The binding's RID in managed references registry
- The serialized data's `uxmlAssetId` field
- Matches the element's `m_Id` in m_VisualElementAssets

**Method 2: By Element Name and Type**
- Use serialized data's `name` field
- Match to element's `m_Name` attribute in XML
- Combined with element type for disambiguation

### Step 5: Rebuild ManagedReferencesRegistry

Create Unity structure:
```csharp
ManagedReferencesRegistry {
  version: 2
  RefIds: [
    ReferencedObject {
      rid: {RID}
      type: ReferencedManagedType {
        class: "SIText/UxmlSerializedData"
        ns: "SI.Bindable"
        asm: "SI.Core"
      }
      data: UxmlSerializedData {
        uxmlAssetId: {ELEMENT_M_ID}
        name: "{ELEMENT_NAME}"
        // ... binding properties ...
        TextBinding: BindingMethod {
          m_kind: 2
          m_direct: BindingPath {
            m_path: "{BINDING_PATH}"
          }
        }
      }
    }
  ]
}
```

## Example Complete UXML with Bindings

```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <!-- UXML Templates Used In This File -->
    <!-- Template: layout-divider-solid-horizontal -->

    <!-- ============================================ -->
    <!-- DATA BINDINGS (connects UI to game data)   -->
    <!-- Format: BindingType[rid=ID, name="..."]     -->
    <!--   key: value                               -->
    <!-- ============================================ -->

    <!-- UxmlSerializedData[rid=1000] -->
    <!--   Parameters: -->
    <!--     - club -->
    <!--  -->
    <!-- UxmlSerializedData[rid=1028] -->
    <!--   TextBinding: Club.Background -->
    <!--  -->
    <!-- UxmlSerializedData[rid=1038] -->
    <!--   Binding: Club.ReservesTeam -->
    <!--  -->
    <!-- UxmlSerializedData[rid=1043] -->
    <!--   TextBinding: Club.ReservesTeam.Name -->
    <!--  -->
    <!-- UxmlSerializedData[rid=1052] -->
    <!--   Mappings: -->
    <!--     - team -> Club.MainTeam -->
    <!--  -->

    <UXML>
        <!-- SI.Bindable.BindingExpect -->
        <!-- BINDING[rid=1000]: Parameters: club -->
        <BindingExpect>
            <VisualElement>
                <!-- SI.Bindable.SIText -->
                <!-- BINDING[rid=1028]: TextBinding: Club.Background -->
                <SIText class="body-small-12px-regular" />

                <!-- SI.Bindable.SIVisible -->
                <!-- BINDING[rid=1038]: Binding: Club.ReservesTeam -->
                <SIVisible name="reserves-visible">
                    <!-- SI.Bindable.SIText -->
                    <!-- BINDING[rid=1043]: TextBinding: Club.ReservesTeam.Name -->
                    <SIText name="reserves-name" />
                </SIVisible>

                <!-- SI.Bindable.BindingRemapper -->
                <!-- BINDING[rid=1052]: Mappings: team -> Club.MainTeam -->
                <BindingRemapper>
                    <!-- Child elements use "team" variable -->
                </BindingRemapper>
            </VisualElement>
        </BindingExpect>
    </UXML>
</ui:UXML>
```

## Import Algorithm

### Pseudo-code for Parsing

```python
def parse_uxml_bindings(uxml_file):
    bindings = {}

    # Parse header bindings
    header_section = extract_section_between(
        "DATA BINDINGS",
        "<UXML>"
    )

    for binding_block in parse_binding_blocks(header_section):
        rid, name, properties = parse_binding_block(binding_block)
        bindings[rid] = {
            'name': name,
            'properties': properties,
            'type': 'header'
        }

    # Parse inline bindings
    for element in parse_xml_elements(uxml_file):
        inline_binding = extract_inline_binding(element.preceding_comments)

        if inline_binding:
            rid, properties = parse_inline_binding(inline_binding)

            # Merge with header binding
            if rid in bindings:
                bindings[rid]['element_id'] = element.id
                bindings[rid]['element_name'] = element.name
                bindings[rid]['element_type'] = element.type

    return bindings

def parse_binding_block(text):
    # Parse: <!-- UxmlSerializedData[rid=1000, name="..."] -->
    match = re.match(r'<!-- UxmlSerializedData\[rid=(\d+)(?:, name="([^"]*)")?\] -->', text)
    rid = int(match.group(1))
    name = match.group(2) or ''

    properties = {}
    lines = text.split('\n')[1:]  # Skip first line

    current_key = None
    current_list = []

    for line in lines:
        if '<!--  -->' in line:
            break

        # Simple property: <!--   key: value -->
        if ': ' in line and not line.strip().startswith('- '):
            if current_key:
                properties[current_key] = current_list

            key, value = parse_property_line(line)
            if value:
                properties[key] = value
                current_key = None
            else:
                current_key = key
                current_list = []

        # List item: <!--     - item -->
        elif line.strip().startswith('- '):
            item = parse_list_item(line)
            current_list.append(item)

    if current_key:
        properties[current_key] = current_list

    return rid, name, properties
```

### Pseudo-code for Rebuilding

```python
def rebuild_managed_references(bindings, elements):
    ref_registry = {
        'version': 2,
        'RefIds': []
    }

    for rid, binding_data in bindings.items():
        # Find matching element
        element = find_element_by_binding(binding_data, elements)

        if not element:
            continue

        # Create referenced object
        ref_obj = {
            'rid': rid,
            'type': create_managed_type(binding_data),
            'data': create_serialized_data(binding_data, element)
        }

        ref_registry['RefIds'].append(ref_obj)

    return ref_registry

def create_serialized_data(binding_data, element):
    data = {
        'uxmlAssetId': element['m_Id'],
        'name': binding_data.get('name', ''),
        'bindings': [],
        'tooltip': '',
        # ... other standard fields ...
    }

    # Add binding-specific properties
    for key, value in binding_data['properties'].items():
        if key == 'TextBinding':
            data['TextBinding'] = create_binding_method(value)
        elif key == 'Binding':
            data['Binding'] = create_binding_method(value)
        elif key == 'Mappings':
            data['Mappings'] = create_remap_info_list(value)
        elif key == 'Parameters':
            data['Parameters'] = create_parameter_list(value)
        elif key == 'ValueVariables':
            data['ValueVariables'] = create_variable_list(value)

    return data

def create_binding_method(path_string):
    return {
        'm_kind': 2 if path_string else 0,
        'm_direct': {
            'm_path': path_string
        },
        'm_visualFunction': None
    }

def create_remap_info_list(mappings):
    result = []
    for mapping in mappings:
        from_part, to_part = mapping.split(' -> ')
        result.append({
            'from_': from_part.strip(),
            'to': {
                'm_path': to_part.strip()
            }
        })
    return result
```

## Validation

### Required Fields

Header binding must have:
- `rid` (integer, > 0)

Element binding should have:
- At least one binding property (TextBinding, Binding, Mappings, Parameters, etc.)

### Constraints

- RID must be unique within file
- Element names can be empty strings
- Binding paths can be empty for unassigned bindings
- Array properties can be empty lists

### Consistency Checks

1. **RID Matching**: Header RID should match inline RID
2. **Element Existence**: uxmlAssetId should match an element m_Id
3. **Name Consistency**: If name is provided, it should match element's m_Name
4. **Type Consistency**: Binding type should match element type

## Version History

### Version 1.0 (Current)
- Initial format specification
- Header and inline binding comments
- Support for all SI.Bindable components
- XML character escaping
- Array and simple property types

## Future Extensions

Potential additions to format:

1. **Binding Validation Metadata**
   ```xml
   <!-- BINDING[rid=1000, validated=true, source_type="Club"] -->
   ```

2. **Binding Source Documentation**
   ```xml
   <!-- BINDING[rid=1000]: TextBinding: Club.Name -->
   <!--   Source: FM.Core.Club.Name (string) -->
   ```

3. **Runtime Binding State**
   ```xml
   <!-- BINDING[rid=1000, runtime_only=false] -->
   ```

4. **Binding Groups**
   ```xml
   <!-- BINDING_GROUP[name="club_info"]: rids=1000,1028,1038 -->
   ```

## Tools

Recommended tools for working with binding format:

1. **Parser**: Python script using regex and XML parsing
2. **Validator**: Check binding consistency and completeness
3. **Converter**: UXML comments ↔ Unity binary format
4. **Diff Tool**: Compare binding changes between versions

## License

This specification is part of the FM Skin Builder project.
