# Unity StyleSheet (USS) Serialization Technical Documentation

## Overview

This document explains how Unity's StyleSheet (USS) serialization works and how FM Skin Builder patches USS properties while preserving Unity's serialization integrity.

## Unity StyleSheet Structure

Unity StyleSheets are MonoBehaviour assets with the following key arrays:

```csharp
class StyleSheet : ScriptableObject {
    string[] strings;     // String values, variable names, resource paths
    ColorRGBA[] colors;   // Color values (RGBA floats 0-1)
    float[] floats;       // Numeric values with units

    StyleRule[] m_Rules;  // CSS rules
    StyleComplexSelector[] m_ComplexSelectors;  // Selector definitions
}
```

Each property value has:
- `m_ValueType` (int): Type identifier (see below)
- `valueIndex` (int): Index into the appropriate array

## Unity Value Types

| Type | Name | Array | Description | Example |
|------|------|-------|-------------|---------|
| 1 | Keyword | strings | Boolean/enum keywords | `visible`, `hidden`, `bold` |
| 2 | Float | floats | Numeric values with units | `12px`, `1.5em`, `0.9` |
| 3 | String | strings | Variable references | `var(--my-color)` |
| 4 | Color | colors | RGBA color values | `rgba(1, 0, 0, 1)` |
| 7 | AssetReference | strings | Resource paths | `resource://fonts/MyFont` |
| 8 | Enum | strings | Enum values | `normal`, `italic` |
| 10 | Variable | strings | Variable references | `--my-variable` |

## Key Insights

### 1. Type 7 Uses String Paths, Not Binary References

**Important**: Unity USS Type 7 (AssetReference) stores **string paths** like `"resource://fonts/MyFont"`, NOT binary `PPtr<Object>` references with FileID/PathID.

This is different from Unity's typical MonoBehaviour serialization:

```csharp
// MonoBehaviour serialization (typical Unity assets)
public class MyComponent : MonoBehaviour {
    public Font myFont;  // Stored as PPtr<Font> with FileID + PathID
}

// USS StyleSheet (UI Toolkit)
// -unity-font: url('resource://fonts/MyFont')
// Stored as: Type 7, strings[idx] = "resource://fonts/MyFont"
// Unity resolves this at runtime via ResourceLoader
```

**Why string paths?**
- USS files are text-based (.uss files)
- Must be editable in text editors
- Runtime resolution allows dynamic loading
- Cross-platform compatibility

### 2. Array Index Preservation

When patching existing values, we **MUST** preserve array indices to maintain references:

```python
# CORRECT - Update in-place
if value_index is not None and 0 <= value_index < len(floats):
    floats[value_index] = new_value  # Preserves index

# WRONG - Would break references
floats.append(new_value)  # Creates new index
# Other properties referencing old index would break
```

### 3. Variable Reference Conversion

When a CSS variable definition only contains a reference (e.g., `--my-size: var(--base-size)`), and the user provides a literal value, we convert the reference to a literal:

**Before:**
```css
/* Original USS */
--my-font-size: var(--base-font-size);  /* Type 3 reference */
```

**After user provides:**
```css
/* User's CSS */
--my-font-size: 16px;
```

**Result:**
```css
/* Patched USS */
--my-font-size: 16px;  /* Type 2 literal float */
```

This ensures the new value survives even without updating the referenced variable.

## Patching Strategy

### Phase 1: Direct Property Patches

For properties that match CSS variable names:

1. Find property by `m_Name`
2. Check if value is color, float, keyword, or resource
3. If existing literal value exists (Type 2/4/7/8):
   - Update in-place, preserving index
4. If only variable reference exists (Type 3/10):
   - Convert to literal (Type 2/4/7/8)
   - Append to appropriate array

### Phase 2: Convert Variable References

For CSS variable definitions without literals:

1. Find root-level variable (property with `--var-name`)
2. Check if it has a literal value
3. If only reference (Type 3/8/10):
   - Parse user's value
   - Create new literal in appropriate array
   - Update value handle to point to literal

### Phase 3: Selector Property Overrides

For selector-specific overrides (e.g., `.button { font-size: 16px; }`):

1. Match selector and property name
2. Follow same patching strategy as Phase 1
3. Track which assets were modified (for conflict detection)

## Examples

### Example 1: Updating Existing Float

```python
# Original USS
floats[5] = 14.0  # font-size
prop.m_Values[0] = { m_ValueType: 2, valueIndex: 5 }

# User provides: font-size: 16px
# Patch:
floats[5] = 16.0  # Update in-place
# valueIndex stays 5, references preserved
```

### Example 2: Converting Reference to Literal

```python
# Original USS
strings[10] = "--base-size"  # Variable reference
prop.m_Values[0] = { m_ValueType: 3, valueIndex: 10 }

# User provides: --my-size: 20px
# Patch:
floats.append(20.0)  # New float
new_index = len(floats) - 1
prop.m_Values[0] = { m_ValueType: 2, valueIndex: new_index }
# Converted from Type 3 (variable) to Type 2 (float)
```

### Example 3: Resource Path Update

```python
# Original USS
strings[15] = "resource://fonts/OldFont"
prop.m_Values[0] = { m_ValueType: 7, valueIndex: 15 }

# User provides: -unity-font: url('resource://fonts/NewFont')
# Patch:
strings[15] = "resource://fonts/NewFont"  # Update in-place
# valueIndex stays 15, Type stays 7
```

## Type Priority for Properties

Some properties accept multiple types. We use this priority:

```python
PROPERTY_TYPE_MAP = {
    "width": PropertyType("width", [2, 1, 8], 2),  # Float (2) or keyword (1/8)
    # Priority: Try Type 2 (float) first, then Type 1/8 (keyword)
}
```

When patching:
1. Check if value matches primary type (Type 2 for width)
2. If parsing fails, try secondary type
3. Use `default_type` when creating new values

## Backwards Compatibility

### Colors (Type 4)

All existing color patching logic is preserved:

```python
# Check if it's a color property
if _is_color_property(prop_name, value_str):
    # Use existing color patching logic
    # hex_to_rgba(), update colors array, etc.
else:
    # New: Handle non-color properties
    # Float, keyword, resource patching
```

### CSS Collection

The CSS collection system now supports all property types:

```python
# Old (colors only)
file_vars = load_css_vars(css_file)  # Dict[str, str] (hex colors)

# New (all types)
file_vars = load_css_properties(css_file)  # Dict[str, Any]
# Values can be: "#FF0000", "16px", "bold", "url('...')"
```

## Limitations and Caveats

### 1. Resource Resolution is Runtime

Font changes via `-unity-font: url('resource://fonts/NewFont')` require:
- Font asset exists in Unity project's Resources folder
- Font name matches the resource path
- Unity can resolve the path at runtime

We **cannot** create Font assets or modify Font asset bundles.

### 2. External Asset References

If a USS property references an asset in a different bundle (external FileID), we only update the string path. Unity handles the actual asset loading.

### 3. CSS Variable Chains

For complex variable chains like:
```css
--base: #FF0000;
--primary: var(--base);
--button-color: var(--primary);
```

We only patch the final variable that matches user input. Intermediate references are preserved.

### 4. Shorthand Properties

Properties like `padding: 10px 20px` are currently stored as single values. Unity may expand them internally, but we patch the shorthand form.

## Testing Strategy

### Unit Tests

Test value parsing:
- `test_value_parsers.py`: 43 tests for float, keyword, resource parsing

### Integration Tests

Test property patching:
- Update existing values in-place
- Convert variable references to literals
- Handle all value types (2, 4, 7, 8)

### Bundle Tests

Test with real Unity bundles:
- Verify array indices preserved
- Check Unity can load patched bundles
- Confirm runtime resource resolution works

## References

- [Unity USS Properties Reference](https://docs.unity3d.com/Manual/UIE-USS-Properties-Reference.html)
- [Unity UI Toolkit](https://docs.unity3d.com/Manual/UIElements.html)
- [Unity Serialization](https://docs.unity3d.com/Manual/script-Serialization.html)
- UnityPy Documentation: `bundle.env.objects` iteration
