# UXML Manipulation Guide

Complete guide to editing Unity UI Toolkit layouts using the UXML import/export pipeline.

---

## Overview

The UXML pipeline allows you to:
- ✅ Export VTA to human-readable UXML
- ✅ Edit UXML in any text editor
- ✅ Import modified UXML back to VTA format
- ✅ Maintain perfect order and structure
- ✅ Manipulate styles, classes, and elements

---

## Table of Contents

1. [Stylesheet References (External CSS)](#stylesheet-references)
2. [Inline Styles](#inline-styles)
3. [Class Manipulation](#class-manipulation)
4. [Element Manipulation](#element-manipulation)
5. [Complete Examples](#complete-examples)

---

## Stylesheet References

Unity UI Toolkit uses USS (Unity Style Sheets) files for styling, similar to CSS.

### How It Works

When you export a VTA, stylesheet references appear as `<Style>` elements:

```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <Style src="#9865314e7997c984d9af1b32b9bdf2ee"/>
  <Style src="#a1b2c3d4e5f6789012345678901234ab"/>

  <ui:VisualElement class="my-styled-element">
    <!-- Elements use classes defined in the USS files -->
  </ui:VisualElement>
</ui:UXML>
```

### Stylesheet Format

- **GUID Format**: `#` + 32-character hex GUID
- **Unity Convention**: GUIDs reference USS files in the Unity project
- **Multiple Stylesheets**: You can have multiple `<Style>` elements

### What You Can Do

**View which stylesheets are linked:**
```python
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter

exporter = UXMLExporter()
doc = exporter.export_visual_tree_asset(vta_data)
print(f"Stylesheets: {doc.stylesheets}")
```

**Add a new stylesheet reference:**
```xml
<!-- Add this at the top after other Style elements -->
<Style src="#your-new-stylesheet-guid"/>
```

**Remove a stylesheet:**
```xml
<!-- Just delete the <Style> element -->
```

**Reorder stylesheets:**
```xml
<!-- Stylesheets are applied in order, so reordering affects priority -->
<Style src="#base-styles"/>
<Style src="#theme-overrides"/>  <!-- Applied last, takes priority -->
```

### Limitations

- **GUIDs Only**: The pipeline preserves GUIDs but doesn't resolve them to filenames
- **No USS Content**: USS file contents are not exported (use Unity's USS editor)
- **Reference Only**: Stylesheet references work for reimport but don't modify USS files

---

## Inline Styles

Inline styles are CSS-like style declarations directly on elements.

### How It Works

Inline styles use the `style` attribute:

```xml
<ui:Label text="Hello" style="color: #FF0000; font-size: 24px;"/>
```

### Syntax

```
style="property1: value1; property2: value2;"
```

**Common Properties:**
- `color: #RRGGBB` or `rgb(r, g, b)`
- `font-size: 16px`
- `font-weight: bold`
- `background-color: #FFFFFF`
- `margin: 10px` or `margin-left: 5px`
- `padding: 10px`
- `width: 200px` or `width: 50%`
- `height: 100px`
- `flex-direction: row`
- `align-items: center`
- `justify-content: space-between`

### Examples

**Simple styling:**
```xml
<ui:Button text="Click Me" style="color: #FFFFFF; background-color: #007ACC;"/>
```

**Layout properties:**
```xml
<ui:VisualElement style="flex-direction: row; padding: 10px;">
  <ui:Label text="Name:" style="width: 100px;"/>
  <ui:TextField style="flex-grow: 1;"/>
</ui:VisualElement>
```

**Combining with classes:**
```xml
<!-- Class from USS file provides base styling -->
<!-- Inline style overrides specific properties -->
<ui:Label class="title-text" style="color: #FF0000;"/>
```

### Programmatic Manipulation

**Python API:**
```python
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from pathlib import Path

# Import UXML
importer = UXMLImporter()
doc = importer.import_uxml(Path("layout.uxml"))

# Find element and modify style
label = doc.find_element_by_name("my-label")
for attr in label.attributes:
    if attr.name == 'style':
        attr.value = "color: #00FF00; font-size: 32px;"
        break
else:
    # Add style if it doesn't exist
    from fm_skin_builder.core.uxml.uxml_ast import UXMLAttribute
    label.attributes.append(UXMLAttribute(
        name="style",
        value="color: #00FF00; font-size: 32px;"
    ))

# Export back
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter
exporter = UXMLExporter()
exporter.write_uxml(doc, Path("layout_modified.uxml"))
```

---

## Class Manipulation

Classes link elements to styles defined in USS files.

### How It Works

Elements can have multiple CSS classes:

```xml
<ui:Button class="primary-button large-text"/>
<ui:Label class="title-text bold"/>
```

### Adding Classes

**In UXML:**
```xml
<!-- Add space-separated class names -->
<ui:VisualElement class="container flex-row">
  <!-- Add another class -->
  <ui:Label class="text-primary bold uppercase"/>
</ui:VisualElement>
```

**In Python:**
```python
# Using helper methods
element = doc.find_element_by_name("my-button")
element.add_class("active")
element.add_class("highlighted")

# Or manually
for attr in element.attributes:
    if attr.name == 'class':
        classes = attr.value.split()
        classes.append("new-class")
        attr.value = " ".join(classes)
        break
```

### Removing Classes

**In UXML:**
```xml
<!-- Before -->
<ui:Button class="primary-button large-text active"/>

<!-- After (removed 'active') -->
<ui:Button class="primary-button large-text"/>
```

**In Python:**
```python
# Using helper method
element.remove_class("active")

# Or manually
for attr in element.attributes:
    if attr.name == 'class':
        classes = attr.value.split()
        classes.remove("active")
        attr.value = " ".join(classes)
        break
```

### Modifying Classes

**Replace all classes:**
```xml
<!-- Before -->
<ui:Label class="old-style deprecated"/>

<!-- After -->
<ui:Label class="new-style modern"/>
```

**Python:**
```python
for attr in element.attributes:
    if attr.name == 'class':
        attr.value = "new-class1 new-class2"
        break
```

### Querying Classes

**Python:**
```python
# Get all classes on an element
classes = element.get_classes()
print(classes)  # ['primary-button', 'large-text']

# Find all elements with a specific class
buttons = doc.find_elements_by_class("primary-button")
```

---

## Element Manipulation

Add, remove, or modify UI elements in the hierarchy.

### Adding Elements

**In UXML (text editing):**
```xml
<ui:VisualElement name="container">
  <ui:Label text="Existing element"/>

  <!-- Add a new button -->
  <ui:Button name="new-btn" text="Click Me" class="primary-button"/>

  <!-- Add a text field -->
  <ui:TextField name="input" placeholder-text="Enter text..."/>
</ui:VisualElement>
```

**In Python:**
```python
from fm_skin_builder.core.uxml.uxml_ast import UXMLElement, UXMLAttribute

# Create new element
new_button = UXMLElement(
    element_type="Button",
    attributes=[
        UXMLAttribute(name="name", value="new-btn"),
        UXMLAttribute(name="text", value="Click Me"),
        UXMLAttribute(name="class", value="primary-button"),
    ]
)

# Add to parent
container = doc.find_element_by_name("container")
container.children.append(new_button)
```

### Removing Elements

**In UXML:**
```xml
<!-- Just delete the element -->
<ui:VisualElement name="container">
  <ui:Label text="Keep this"/>
  <!-- Deleted: <ui:Button name="remove-me"/> -->
  <ui:TextField text="Keep this too"/>
</ui:VisualElement>
```

**In Python:**
```python
# Remove by index
container.children.pop(1)

# Remove by finding element
for i, child in enumerate(container.children):
    if child.get_attribute("name") == "remove-me":
        container.children.pop(i)
        break

# Remove all elements of a type
container.children = [
    child for child in container.children
    if child.element_type != "Button"
]
```

### Modifying Elements

**Change element type** (requires recreating):
```xml
<!-- Before -->
<ui:Label name="my-text" text="Hello"/>

<!-- After (changed to Button) -->
<ui:Button name="my-text" text="Hello"/>
```

**Modify attributes:**
```xml
<!-- Before -->
<ui:Button name="btn1" text="Old Text" class="primary"/>

<!-- After -->
<ui:Button name="btn1" text="New Text" class="primary disabled"/>
```

**Python:**
```python
# Modify text
button = doc.find_element_by_name("btn1")
button.set_attribute("text", "New Text")

# Add new attribute
button.set_attribute("tooltip", "Click to submit")

# Modify multiple attributes
for attr in button.attributes:
    if attr.name == "text":
        attr.value = "Updated Text"
    elif attr.name == "class":
        attr.value += " disabled"
```

### Moving Elements

**In UXML (cut and paste):**
```xml
<!-- Before -->
<ui:VisualElement name="left-panel">
  <ui:Button name="move-me" text="I will move"/>
</ui:VisualElement>
<ui:VisualElement name="right-panel">
</ui:VisualElement>

<!-- After -->
<ui:VisualElement name="left-panel">
</ui:VisualElement>
<ui:VisualElement name="right-panel">
  <ui:Button name="move-me" text="I will move"/>
</ui:VisualElement>
```

**In Python:**
```python
# Find source and destination
left_panel = doc.find_element_by_name("left-panel")
right_panel = doc.find_element_by_name("right-panel")

# Move element
button = left_panel.children.pop(0)
right_panel.children.append(button)
```

### Reordering Elements

**In UXML:**
```xml
<!-- Order matters! Elements render in document order -->
<ui:VisualElement>
  <ui:Label text="First"/>
  <ui:Button text="Second"/>
  <ui:TextField text="Third"/>
</ui:VisualElement>
```

**In Python:**
```python
# Swap two elements
container.children[0], container.children[1] = \
    container.children[1], container.children[0]

# Sort by name
container.children.sort(
    key=lambda e: e.get_attribute("name") or ""
)

# Move to front
element = container.children.pop(2)
container.children.insert(0, element)
```

---

## Complete Examples

### Example 1: Stylesheet and Class Management

```python
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter
from pathlib import Path

# Import
importer = UXMLImporter()
doc = importer.import_uxml(Path("panel.uxml"))

# View stylesheets
print(f"Current stylesheets: {doc.stylesheets}")

# Add a stylesheet (you need the GUID)
doc.stylesheets.append("newstyle-guid-here")

# Modify classes on all buttons
for button in doc.find_elements_by_type("Button"):
    button.remove_class("old-style")
    button.add_class("new-style")
    button.add_class("animated")

# Export
exporter = UXMLExporter()
exporter.write_uxml(doc, Path("panel_updated.uxml"))
```

**Result UXML:**
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
  <Style src="#original-stylesheet-guid"/>
  <Style src="#newstyle-guid-here"/>

  <ui:Button class="new-style animated"/>
  <ui:Button class="new-style animated"/>
</ui:UXML>
```

---

### Example 2: Inline Style Theming

```python
# Import
doc = importer.import_uxml(Path("dialog.uxml"))

# Apply dark theme using inline styles
for label in doc.find_elements_by_type("Label"):
    label.set_attribute("style", "color: #FFFFFF; background-color: #2D2D30;")

for button in doc.find_elements_by_type("Button"):
    button.set_attribute("style", "color: #FFFFFF; background-color: #007ACC;")

# Export
exporter.write_uxml(doc, Path("dialog_dark.uxml"))
```

**Result UXML:**
```xml
<ui:Label text="Title" style="color: #FFFFFF; background-color: #2D2D30;"/>
<ui:Button text="OK" style="color: #FFFFFF; background-color: #007ACC;"/>
```

---

### Example 3: Dynamic Form Builder

```python
from fm_skin_builder.core.uxml.uxml_ast import UXMLElement, UXMLAttribute

# Import base template
doc = importer.import_uxml(Path("form_template.uxml"))
container = doc.find_element_by_name("form-container")

# Define form fields
fields = [
    {"label": "Name", "type": "TextField", "placeholder": "Enter your name"},
    {"label": "Email", "type": "TextField", "placeholder": "you@example.com"},
    {"label": "Age", "type": "IntegerField", "placeholder": "0"},
]

# Add fields dynamically
for field_def in fields:
    # Create row
    row = UXMLElement(
        element_type="VisualElement",
        attributes=[UXMLAttribute(name="class", value="form-row")]
    )

    # Add label
    label = UXMLElement(
        element_type="Label",
        attributes=[
            UXMLAttribute(name="text", value=field_def["label"]),
            UXMLAttribute(name="class", value="form-label"),
        ]
    )
    row.children.append(label)

    # Add input
    input_field = UXMLElement(
        element_type=field_def["type"],
        attributes=[
            UXMLAttribute(name="placeholder-text", value=field_def["placeholder"]),
            UXMLAttribute(name="class", value="form-input"),
        ]
    )
    row.children.append(input_field)

    # Add row to container
    container.children.append(row)

# Add submit button
submit = UXMLElement(
    element_type="Button",
    attributes=[
        UXMLAttribute(name="text", value="Submit"),
        UXMLAttribute(name="class", value="submit-button"),
    ]
)
container.children.append(submit)

# Export
exporter.write_uxml(doc, Path("form_generated.uxml"))
```

**Result UXML:**
```xml
<ui:VisualElement name="form-container">
  <ui:VisualElement class="form-row">
    <ui:Label text="Name" class="form-label"/>
    <ui:TextField placeholder-text="Enter your name" class="form-input"/>
  </ui:VisualElement>
  <ui:VisualElement class="form-row">
    <ui:Label text="Email" class="form-label"/>
    <ui:TextField placeholder-text="you@example.com" class="form-input"/>
  </ui:VisualElement>
  <ui:VisualElement class="form-row">
    <ui:Label text="Age" class="form-label"/>
    <ui:IntegerField placeholder-text="0" class="form-input"/>
  </ui:VisualElement>
  <ui:Button text="Submit" class="submit-button"/>
</ui:VisualElement>
```

---

### Example 4: Bulk Updates

```python
# Import
doc = importer.import_uxml(Path("complex_panel.uxml"))

# Find all elements with old naming convention
for element in doc.get_all_elements():
    name = element.get_attribute("name")
    if name and name.startswith("old_"):
        # Update naming convention
        new_name = name.replace("old_", "new_")
        element.set_attribute("name", new_name)

    # Add common class to all containers
    if element.element_type == "VisualElement":
        element.add_class("container-v2")

    # Update deprecated elements
    if element.get_attribute("deprecated") == "true":
        element.add_class("hidden")

# Export
exporter.write_uxml(doc, Path("complex_panel_updated.uxml"))
```

---

## Best Practices

### 1. **Use Stylesheets for Reusable Styles**
```xml
<!-- Good: Reusable, maintainable -->
<Style src="#common-styles"/>
<ui:Button class="primary-button"/>

<!-- Avoid: Duplicated inline styles -->
<ui:Button style="color: #FFF; background: #007ACC; padding: 10px;"/>
<ui:Button style="color: #FFF; background: #007ACC; padding: 10px;"/>
```

### 2. **Use Inline Styles for One-Off Overrides**
```xml
<!-- Good: Base style from class, specific override inline -->
<ui:Label class="title-text" style="color: #FF0000;"/>

<!-- Avoid: Everything inline -->
<ui:Label style="font-size: 24px; font-weight: bold; margin: 10px; color: #FF0000;"/>
```

### 3. **Maintain Semantic Class Names**
```xml
<!-- Good: Describes purpose -->
<ui:Button class="submit-button primary"/>

<!-- Avoid: Describes appearance -->
<ui:Button class="blue-button big"/>
```

### 4. **Keep Element Hierarchy Flat**
```xml
<!-- Good: Shallow hierarchy -->
<ui:VisualElement class="container">
  <ui:Label class="title"/>
  <ui:Button class="action"/>
</ui:VisualElement>

<!-- Avoid: Deep nesting (unless necessary) -->
<ui:VisualElement>
  <ui:VisualElement>
    <ui:VisualElement>
      <ui:Label/>
    </ui:VisualElement>
  </ui:VisualElement>
</ui:VisualElement>
```

### 5. **Use Names for Important Elements**
```xml
<!-- Good: Named for programmatic access -->
<ui:Button name="submit-btn" text="Submit"/>

<!-- OK: No name needed if not referenced -->
<ui:Label text="Description"/>
```

---

## Limitations

### Unity VTA Import
When importing back to Unity's VisualTreeAsset format:
- **Inline styles** are preserved in UXML but NOT in VTA (Unity uses StyleSheets)
- **Stylesheet GUIDs** are preserved but not validated
- **Custom attributes** may be lost (Unity supports specific attributes per element type)

### Round-Trip Compatibility
- **UXML → UXML**: Perfect fidelity ✓
- **VTA → UXML → VTA**: Structure and references preserved ✓
- **Unity Editor**: May need to reassign USS files if GUIDs change

---

## Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Stylesheet References | ✅ Full Support | Import/export GUID references |
| Inline Styles | ✅ Full Support | Round-trip in UXML, not VTA |
| Class Add/Remove | ✅ Full Support | Helper methods available |
| Element Add/Remove | ✅ Full Support | Programmatic or text editing |
| Element Reorder | ✅ Full Support | Order preserved perfectly |
| Attribute Editing | ✅ Full Support | All attributes supported |
| Template References | ✅ Full Support | See TEMPLATE_AND_ORDER_FIXES_COMPLETE.md |
| Data Bindings | ✅ Full Support | See BINDING_EXTRACTION_COMPLETE.md |

---

## Next Steps

1. **Experiment**: Try editing a simple UXML file
2. **Test Round-Trip**: Export → Edit → Import → Verify
3. **Build Tools**: Create scripts for common modifications
4. **Document Styles**: Map USS GUIDs to filenames for your project

Happy editing! 🎨
