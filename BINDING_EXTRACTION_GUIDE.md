# Data Binding Extraction Guide

## Overview

The UXML exporter now extracts data binding information from Unity's VisualTreeAsset and exports it as human-readable UXML attributes. This allows you to see what data is bound to UI elements and modify these bindings by editing the UXML files.

## What Are Data Bindings?

In Unity UI Toolkit and FM's custom SI.Bindable framework, UI elements can be "bound" to data sources. This means:
- A text element can display data from a specific field (e.g., "Person.Name")
- A visual element's visibility can be controlled by a boolean value (e.g., "config.ShowPhonePanels")
- Variable names can be mapped to data paths (e.g., "team" → "Human.Team")

## Supported Binding Types

### 1. Text Binding (`text-binding`)

Used by SIText elements to bind displayed text to a data field.

**Example:**
```xml
<ui:SIText text-binding="Person.Name" class="player-name"/>
<ui:SIText text-binding="Person.JobString" class="player-job"/>
```

**Editing:**
```xml
<!-- Change from showing player name to player age -->
<ui:SIText text-binding="Person.Age" class="player-name"/>

<!-- Change from showing job to showing nationality -->
<ui:SIText text-binding="Person.Nationality.Name" class="player-job"/>
```

### 2. Data Binding (`data-binding`)

Used by various bindable elements (BindableSwitchElement, SIImage, etc.) to bind their behavior or content to data.

**Example:**
```xml
<ui:BindableSwitchElement data-binding="config.ShowPhonePanels" class="base-template-grow"/>
```

**Editing:**
```xml
<!-- Change which config option controls this element -->
<ui:BindableSwitchElement data-binding="config.ShowTabletPanels" class="base-template-grow"/>
```

### 3. Binding Mappings (`binding-mappings`)

Used by BindingRemapper to map local variable names to actual data paths. Format: `variable1=Path1;variable2=Path2`

**Example:**
```xml
<ui:BindingRemapper binding-mappings="yearindex=Year.PropertyValue;team=Human.Team" class="base-template-grow"/>
```

**Editing:**
```xml
<!-- Change from Year to Month, and from Team to Club -->
<ui:BindingRemapper binding-mappings="yearindex=Month.PropertyValue;team=Human.Club" class="base-template-grow"/>
```

### 4. Selection Bindings

Used by TabbedGridLayoutElement for tab selection state.

**Attributes:**
- `current-selected-id-binding`: Current selected tab ID
- `selection-binding`: Selected tab binding path
- `selected-tab-binding`: Selected tab data binding

**Example:**
```xml
<ui:TabbedGridLayoutElement
    selection-binding="calendartab"
    current-selected-id-binding="calendartab"
    class="tabbed-layout"/>
```

## Visual Function Bindings

Some bindings use "visual functions" instead of direct paths. These are marked as `[VisualFunction]`:

```xml
<ui:SIText text-binding="[VisualFunction]" class="formatted-text"/>
```

Visual function bindings cannot be modified as they use complex transformation logic defined elsewhere.

## Real-World Example: CalendarTool

**Original Export:**
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="../../UIElementsSchema/UIElements.xsd"
         editor-extension-mode="False">
  <ui:BindingRoot class="base-template-grow calendar-button-group">
    <ui:BindingVariables class="base-template-grow">
      <ui:BindingRemapper class="base-template-grow calender-button-group"
                          binding-mappings="yearindex=Year.PropertyValue;team=Human.Team">
        <ui:BindableSwitchElement class="base-template-grow"
                                   data-binding="config.ShowPhonePanels"/>
      </ui:BindingRemapper>
    </ui:BindingVariables>
  </ui:BindingRoot>
</ui:UXML>
```

**Modified Version (Example Changes):**
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="../../UIElementsSchema/UIElements.xsd"
         editor-extension-mode="False">
  <ui:BindingRoot class="base-template-grow calendar-button-group">
    <ui:BindingVariables class="base-template-grow">
      <!-- Changed Year to Month, Team to Club -->
      <ui:BindingRemapper class="base-template-grow calender-button-group"
                          binding-mappings="yearindex=Month.PropertyValue;team=Human.Club">
        <!-- Changed from ShowPhonePanels to ShowTabletPanels -->
        <ui:BindableSwitchElement class="base-template-grow"
                                   data-binding="config.ShowTabletPanels"/>
      </ui:BindingRemapper>
    </ui:BindingVariables>
  </ui:BindingRoot>
</ui:UXML>
```

## Common Use Cases

### Changing Player Attributes Display

```xml
<!-- Before: Show player name -->
<ui:SIText text-binding="Person.Name"/>

<!-- After: Show player age -->
<ui:SIText text-binding="Person.Age"/>
```

### Swapping Left/Right Foot Display

```xml
<!-- Before: Show left foot ability -->
<ui:SIText text-binding="Player.LeftFoot"/>

<!-- After: Show right foot ability -->
<ui:SIText text-binding="Player.RightFoot"/>
```

### Changing Team to Club

```xml
<!-- Before: Bind to team -->
<ui:BindingRemapper binding-mappings="team=Human.Team"/>

<!-- After: Bind to club -->
<ui:BindingRemapper binding-mappings="team=Human.Club"/>
```

### Changing Year to Month

```xml
<!-- Before: Bind to year -->
<ui:BindingRemapper binding-mappings="yearindex=Year.PropertyValue"/>

<!-- After: Bind to month -->
<ui:BindingRemapper binding-mappings="monthindex=Month.PropertyValue"/>
```

## Workflow

### 1. Export with Bindings

```python
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter
from pathlib import Path

# Export VTA with bindings
exporter = UXMLExporter()
doc = exporter.export_visual_tree_asset(vta_data)
exporter.write_uxml(doc, Path("my_ui.uxml"))
```

The exported UXML will contain binding attributes like:
```xml
<ui:SIText text-binding="Person.Name" class="player-name"/>
```

### 2. Edit Bindings

Open the UXML file and modify the binding paths:
```xml
<!-- Change from Name to Age -->
<ui:SIText text-binding="Person.Age" class="player-name"/>
```

### 3. Import Modified UXML

*Note: Import functionality with binding support is planned for future implementation.*

## Technical Details

### How Bindings Are Stored

Unity stores binding data in the VisualTreeAsset's `references` field:
- Each element has a reference ID (rid) that maps to a UxmlSerializedData entry
- The UxmlSerializedData contains binding information:
  - `TextBinding`: BindingMethod with m_kind and m_direct.m_path
  - `Binding`: BindingMethod for general bindings
  - `Mappings`: Array of from/to mappings
  - `CurrentSelectedIdBinding`, `SelectionBinding`, etc.

### Binding Types

- **Direct Binding (m_kind=1)**: Simple path binding (e.g., "Person.Name")
- **Visual Function (m_kind=2)**: Complex transformation (marked as `[VisualFunction]`)

### Attribute Format

All binding attributes use lowercase-with-dashes naming:
- `text-binding` (not `TextBinding`)
- `data-binding` (not `DataBinding`)
- `binding-mappings` (not `BindingMappings`)

This follows UXML/XML conventions and makes attributes easily distinguishable from Unity's native UXML attributes.

## Limitations

1. **Visual Functions**: Cannot be edited as they reference complex transformation logic
2. **Template Bindings**: Bindings in template instances may not be directly visible
3. **Import**: Binding import functionality is not yet implemented

## Future Enhancements

- [ ] Support importing modified bindings back to VTA
- [ ] Extract ReferenceVariables and ValueVariables from BindingVariables
- [ ] Support additional binding types as discovered
- [ ] Validation of binding paths against data model

## Statistics

From testing with FM26's `ui-panelids-uxml_assets_all.bundle`:
- **587 VTAs** have data bindings
- **490 VTAs** have text bindings
- Successfully tested with CalendarTool, showing:
  - 1 data-binding
  - 1 binding-mappings (with 2 mappings)

---

**Status**: ✅ Binding Extraction Complete

**Commit**: `90aa293` - "feat: add data binding extraction to UXML export"

**Branch**: `claude/uxml-import-export-pipeline-011F7NNuAubpKgmoqPW6SgF2`
