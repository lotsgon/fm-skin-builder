# Phase 3: CSS Augmentation Features

FM Skin Builder now supports **CSS augmentation** - the ability to add completely new CSS variables and selectors that don't exist in the original Unity StyleSheets!

## Overview

Previous phases allowed you to:
- **Modify existing** CSS variables and properties
- **Override existing** selector properties

Phase 3 enables you to:
- **Add new** CSS variables that don't exist in the USS
- **Inject new** CSS selectors/classes with custom properties
- **Extend** Unity UI without modifying original USS files

## Features Implemented

### ✅ Phase 3.1: Add New CSS Variables

Add completely new CSS variables to Unity StyleSheets, even if they don't exist in the original USS.

**Example:**
```css
/* Your custom CSS */
--new-button-size: 48px;
--new-accent-color: #FF6B35;
--new-custom-font: url('resource://fonts/MyCustomFont');
--new-visibility-state: visible;
```

**Result:** These variables are automatically added to the Unity StyleSheet's root rule with correct types:
- Colors → Type 4 (colors array)
- Floats with units → Type 2 (floats array)
- Keywords → Type 8 (strings array)
- Resources → Type 7 (strings array)

Variables are sorted alphabetically for consistent output.

### ✅ Phase 3.2: Inject New CSS Selectors

Add completely new CSS selectors/classes to Unity StyleSheets with custom properties.

**Example:**
```css
/* Your custom CSS */
.my-custom-button {
  width: 200px;
  height: 48px;
  font-size: 16px;
  color: #FFFFFF;
  background-color: #0066FF;
  border-radius: 8px;
}

#special-panel {
  opacity: 0.9;
  visibility: visible;
}

Label {
  -unity-text-align: center;
}
```

**Result:** These selectors are automatically created in the Unity StyleSheet:
- New Rule created for each unique selector
- All properties grouped under the selector
- ComplexSelector structure properly linked to the rule
- Supports: `.class`, `#id`, `element`, `:pseudo` selectors

Multiple properties for the same selector are grouped into one rule.
Multiple different selectors create separate rules with proper linking.

## Implementation Details

### Tracking System

The patching system now tracks which variables and selectors were matched:
```python
matched_css_vars: Set[str] = set()
matched_selectors: Set[Tuple[str, str]] = set()
```

After all existing properties are patched, unmatched items are added to the stylesheet:
```python
unmatched_vars = set(css_vars.keys()) - matched_css_vars
unmatched_selectors = set(selector_overrides.keys()) - matched_selectors
```

### Unity Selector Structure

Unity StyleSheets use a specific structure for selectors:

```python
ComplexSelector {
    ruleIndex: int          # Points to rule in m_Rules array
    m_Selectors: [          # List of simple selectors
        {
            m_Parts: [      # List of selector parts
                {
                    m_Type: int     # Selector type
                    m_Value: str    # Selector value
                }
            ]
        }
    ]
}
```

**Selector Part Types:**
- Type 1: Element/type selector (`Label`, `Button`)
- Type 2: ID selector (`#myid`)
- Type 3: Class selector (`.button`)
- Type 4: Pseudo-class selector (`:hover`, `:active`)

### Parsing Logic

**Class Selector (`.button`):**
```python
part.m_Type = 3
part.m_Value = "button"  # Dot removed
```

**ID Selector (`#myid`):**
```python
part.m_Type = 2
part.m_Value = "myid"  # Hash removed
```

**Element Selector (`Label`):**
```python
part.m_Type = 1
part.m_Value = "Label"
```

**Pseudo Selector (`:hover`):**
```python
part.m_Type = 4
part.m_Value = "hover"  # Colon removed
```

## Testing

Comprehensive test suite with 18 tests:

**Phase 3.1 Tests (8 tests):**
- Add new float, color, keyword, resource variables
- Add multiple new variables at once
- Add variables to existing root rule
- Verify alphabetical sorting
- Handle empty variable sets

**Phase 3.2 Tests (10 tests):**
- Add new class selectors with colors and floats
- Add multiple properties to same selector
- Add multiple different selectors
- Parse class, ID, element, pseudo selectors
- Create ComplexSelector structures
- Handle empty selector sets

All tests passing: ✅ 18/18

## Usage Examples

### Example 1: Add New UI Component Style

```css
/* custom-components.css */
.info-tooltip {
  width: 250px;
  padding: 12px;
  background-color: #2C3E50;
  border-radius: 6px;
  font-size: 12px;
  color: #ECF0F1;
  opacity: 0.95;
}
```

This creates a complete new selector with all properties, even if `.info-tooltip` doesn't exist in the original USS.

### Example 2: Add New CSS Variables

```css
/* custom-variables.css */
--tooltip-width: 250px;
--tooltip-bg: #2C3E50;
--tooltip-text: #ECF0F1;
--tooltip-opacity: 0.95;
```

These variables are added to the root rule and can be referenced by other properties.

### Example 3: Extend Existing Unity UI

```css
/* Enhance Unity's built-in Label element */
Label {
  -unity-text-align: center;
  color: #FFFFFF;
}

/* Add custom ID selector */
#main-title {
  font-size: 32px;
  -unity-font: url('resource://fonts/Montserrat-ExtraBold');
  color: #FFD700;
}
```

You can add properties to existing Unity UI elements or create completely new ID-based selectors.

## Logging

Phase 3 features provide detailed logging:

**Variable Addition:**
```
[NEW VAR - float] theme.uss: --new-size → 20.0 (float index 42)
[NEW VAR - color] theme.uss: --new-color → #FF0000 (color index 15)
[NEW VAR - keyword] theme.uss: --new-visibility → visible (string index 128)
[NEW VAR - resource] theme.uss: --new-font → resource://fonts/MyFont (string index 129)
[ADDED] 4 new CSS variables to theme.uss
```

**Selector Injection:**
```
[NEW SELECTOR - color] theme.uss: .button { color: #FF0000; }
[NEW SELECTOR - float] theme.uss: .button { font-size: 16.0; }
[NEW SELECTOR] theme.uss: Created selector '.button' with 2 properties
[ADDED] 2 new selector properties to theme.uss
```

## Backwards Compatibility

Phase 3 features are **100% backwards compatible**:
- Existing patching behavior unchanged
- Only unmatched variables/selectors are added
- All existing Phase 1 and Phase 2 features work as before
- No breaking changes to CSS syntax

## Performance

- **Efficient tracking**: O(n) time to identify unmatched items
- **Sorted output**: Variables and selectors are sorted for consistent results
- **Grouped properties**: Multiple properties for same selector grouped efficiently
- **Minimal overhead**: Tracking adds negligible performance impact

## Limitations

### Current Limitations

1. **Simple selectors only**: Complex selectors like `.button.primary` or `.panel > .title` are not yet supported
2. **No descendant combinators**: Child (`>`), descendant (` `), sibling (`+`, `~`) combinators not supported
3. **Single-part selectors**: Each selector can only have one part (class, ID, element, or pseudo)

### Future Enhancements (Phase 3.3)

**Full CSS Replacement Mode** (`--replace-css` flag) would enable:
- Complete replacement of Unity StyleSheets
- Generate Unity bundles entirely from CSS files
- Support for complex selectors and combinators
- Ability to create USS from scratch without base bundle

This would be a major architectural change requiring:
- New CLI flag `--replace-css`
- Complete bundle generation pipeline
- Complex selector parsing (e.g., `.button.primary`, `.panel > .title`)
- Descendant/child/sibling combinator support
- USS file generation from scratch

## Technical Architecture

### Code Files Modified

**fm_skin_builder/core/css_patcher.py:**
- Added `matched_css_vars` and `matched_selectors` tracking
- Implemented `_add_new_css_variables()` method
- Implemented `_add_new_css_selectors()` method
- Implemented `_create_complex_selector()` helper
- Implemented `_parse_selector_to_part()` helper
- Integrated augmentation into main patching flow

**fm_skin_builder/core/services.py:**
- Fixed missing `_includes_lower` initialization

**tests/test_css_augmentation.py:**
- 18 comprehensive tests for Phase 3 features
- Tests for variables, selectors, parsing, and edge cases

**docs/PHASE3_CSS_AUGMENTATION.md:**
- This documentation file

### Commits

1. **feat: add support for new CSS variables (Phase 3.1)**
   - Implements variable tracking and addition
   - Adds 8 unit tests
   - Fixes services.py bug

2. **feat: add support for injecting new CSS selectors (Phase 3.2)**
   - Implements selector injection and parsing
   - Adds 10 unit tests
   - Complete Unity ComplexSelector structure support

## Next Steps

To enable Phase 3 features, users simply need to:

1. Add new CSS variables or selectors to their CSS files
2. Run FM Skin Builder as usual
3. New variables/selectors are automatically detected and added

No configuration changes required - it just works!

## See Also

- [Advanced CSS Properties Guide](ADVANCED_CSS_GUIDE.md)
- [Unity StyleSheet Serialization Technical Docs](USS_SERIALIZATION_TECHNICAL.md)
- [Font Implementation Plan](FONT_IMPLEMENTATION_PLAN.md)
