# Smart Variable Placement Implementation

## Summary

Implemented hybrid Option A/B solution for multi-file CSS handling that prevents spam of new variables/selectors across all stylesheets while maintaining convenient global overrides for existing content.

## Changes Made

### 1. Added Primary Stylesheet Configuration

**Files Modified:**
- `fm_skin_builder/core/css_patcher.py`
- `fm_skin_builder/core/services.py`

**New Parameters:**
- `primary_variable_stylesheet`: Target stylesheet for new variables (default: "figmastylevariables")
- `primary_selector_stylesheet`: Target stylesheet for new selectors (default: "figmageneratedstyles")

**Configuration:**
```python
# CssPatchOptions dataclass
@dataclass
class CssPatchOptions:
    primary_variable_stylesheet: Optional[str] = None  # Default: "figmastylevariables"
    primary_selector_stylesheet: Optional[str] = None  # Default: "figmageneratedstyles"
```

### 2. Enhanced _effective_overrides Method

**Change:** Now returns whether stylesheet has explicit targeting

**Signature:**
```python
def _effective_overrides(
    self, stylesheet_name: str
) -> Tuple[Dict[str, str], Dict[Tuple[str, str], str], bool]:
    """Returns (vars_combined, selectors_combined, has_targeted_sources)"""
```

**has_targeted_sources:** `True` if stylesheet is in `asset_map` or `files_by_stem` (explicitly targeted via mapping.json or filename matching)

### 3. Smart Placement Logic (Phase 3.1 & 3.2)

**Phase 3.1 - Variables:**
```python
if unmatched_vars:
    # Only add new variables if:
    # 1. Stylesheet has explicit targeting (mapping.json), OR
    # 2. Stylesheet is the primary_variable_stylesheet
    should_add_vars = has_targeted_sources or (name == primary_variable_stylesheet)

    if should_add_vars:
        # Add variables (with reason logging)
    else:
        # Skip and log which variables were skipped
```

**Phase 3.2 - Selectors:**
```python
if truly_new_selectors:
    # Only add new selectors if:
    # 1. Stylesheet has explicit targeting (mapping.json), OR
    # 2. Stylesheet is the primary_selector_stylesheet
    should_add_selectors = has_targeted_sources or (name == primary_selector_stylesheet)

    if should_add_selectors:
        # Add selectors (with reason logging)
    else:
        # Skip and log which selectors were skipped
```

### 4. Enhanced Logging

**When adding new content:**
```
[PHASE 3.1] Adding 5 new CSS variables to FigmaStyleVariables (primary variable stylesheet)
[ADDED] 5 new CSS variables to FigmaStyleVariables
```

OR

```
[PHASE 3.1] Adding 3 new CSS variables to CustomColors (explicit targeting)
[ADDED] 3 new CSS variables to CustomColors
```

**When skipping:**
```
[PHASE 3.1] Skipping 5 new variables for FigmaGeneratedStyles (not targeted, primary is 'figmastylevariables')
  Variables: --new-color-1, --new-color-2, --new-color-3, --new-color-4, --new-color-5
```

```
[PHASE 3.2] Skipping 2 new selector properties for OtherSheet (not targeted, primary is 'figmageneratedstyles')
  Selectors: .new-class, .another-class
```

---

## Behavior Changes

### ✅ EXISTING Variables (No Change - Still Works Great!)

**Scenario:** User changes `--primary-color: #00FF00` (variable exists in multiple files)

**Old Behavior:** Update in all files that have it ✅

**New Behavior:** Update in all files that have it ✅ (NO CHANGE)

### ❌ NEW Variables (Breaking Change - Fixed Spam!)

**Scenario:** User adds `--new-color: #FF0000` (variable doesn't exist anywhere)

**Old Behavior:**
- Added to FigmaStyleVariables ❌
- Added to FigmaGeneratedStyles ❌
- Added to every other stylesheet ❌❌❌
- Result: SPAM!

**New Behavior:**
- Added to FigmaStyleVariables ONLY ✅ (primary_variable_stylesheet)
- Skipped for all other stylesheets ✅
- Result: Clean and intentional!

### ❌ NEW Selectors (Breaking Change - Fixed Spam!)

**Scenario:** User adds `.new-class { color: red; }` (selector doesn't exist anywhere)

**Old Behavior:**
- Added to every stylesheet ❌❌❌

**New Behavior:**
- Added to FigmaGeneratedStyles ONLY ✅ (primary_selector_stylesheet)
- Skipped for all other stylesheets ✅

---

## User Workflows

### Workflow 1: Modify Existing Variables (Most Common)

**User CSS:**
```css
/* colours.css - global (no mapping) */
:root {
    --primary-color: #00FF00;  /* Existing variable */
    --secondary-color: #FF0000;  /* Existing variable */
}
```

**Result:**
- `--primary-color` updated in ALL files that have it ✅
- `--secondary-color` updated in ALL files that have it ✅
- Works exactly as before!

### Workflow 2: Add Few New Variables (Convenient Default)

**User CSS:**
```css
/* colours.css - global (no mapping) */
:root {
    --new-brand-color: #FF6B00;  /* New variable */
    --new-accent: #0099CC;  /* New variable */
}
```

**Result:**
- Both variables added to FigmaStyleVariables ONLY ✅
- Not added to FigmaGeneratedStyles, OtherStyles, etc. ✅
- Clean output, no spam!

**Logs:**
```
[PHASE 3.1] Adding 2 new CSS variables to FigmaStyleVariables (primary variable stylesheet)
[ADDED] 2 new CSS variables to FigmaStyleVariables

[PHASE 3.1] Skipping 2 new variables for FigmaGeneratedStyles (not targeted, primary is 'figmastylevariables')
  Variables: --new-brand-color, --new-accent
```

### Workflow 3: Many Variables + Explicit Targeting

**User has many variables and wants organized placement:**

**mapping.json:**
```json
{
  "brand-colors": "FigmaStyleVariables",
  "layout-variables": "FigmaGeneratedStyles"
}
```

**brand-colors.css:**
```css
:root {
    --brand-primary: #FF6B00;
    --brand-secondary: #0099CC;
    /* ... 10 more brand colors ... */
}
```

**layout-variables.css:**
```css
:root {
    --spacing-sm: 8px;
    --spacing-md: 16px;
    /* ... 10 more layout variables ... */
}
```

**Result:**
- Brand colors → FigmaStyleVariables ONLY ✅
- Layout variables → FigmaGeneratedStyles ONLY ✅
- Perfect organization!

**Logs:**
```
[PHASE 3.1] Adding 12 new CSS variables to FigmaStyleVariables (explicit targeting)
[ADDED] 12 new CSS variables to FigmaStyleVariables

[PHASE 3.1] Adding 12 new CSS variables to FigmaGeneratedStyles (explicit targeting)
[ADDED] 12 new CSS variables to FigmaGeneratedStyles
```

### Workflow 4: Configure Primary Stylesheets

**User wants different defaults:**

**CLI:**
```bash
fm-skin-builder patch \
  --primary-variable-stylesheet CustomColors \
  --primary-selector-stylesheet BaseStyles
```

**OR config.json:**
```json
{
  "css": {
    "primary_variable_stylesheet": "CustomColors",
    "primary_selector_stylesheet": "BaseStyles"
  }
}
```

**Result:**
- New variables go to CustomColors by default
- New selectors go to BaseStyles by default

---

## Migration Guide

### For Users With Existing Skins

**If you only modify existing variables:**
- ✅ No changes needed
- ✅ Everything works as before

**If you add new variables:**
- 📝 Check where they're added (now goes to FigmaStyleVariables by default)
- 📝 If you want different behavior:
  - Option 1: Use mapping.json to target specific files
  - Option 2: Configure primary stylesheets
  - Option 3: Accept the new default (cleaner output!)

---

## Technical Details

### Targeting Detection

**has_targeted_sources = True when:**
1. Stylesheet name is in `css_data.asset_map` (explicit mapping.json entry)
2. Stylesheet name matches CSS filename stem (auto-matching)

**has_targeted_sources = False when:**
- Stylesheet only receives global CSS (no specific targeting)

### Decision Logic

```python
# For new variables
should_add = (
    has_targeted_sources or  # Explicitly targeted
    (name.lower() == primary_variable_stylesheet)  # Is primary
)

# For new selectors
should_add = (
    has_targeted_sources or  # Explicitly targeted
    (name.lower() == primary_selector_stylesheet)  # Is primary
)
```

### Default Values

```python
# In CssPatcher.__init__
self.primary_variable_stylesheet = (
    primary_variable_stylesheet.lower()
    if primary_variable_stylesheet
    else "figmastylevariables"
)
self.primary_selector_stylesheet = (
    primary_selector_stylesheet.lower()
    if primary_selector_stylesheet
    else "figmageneratedstyles"
)
```

---

## Examples

### Example 1: Global CSS (No Mapping)

**Setup:**
- colours.css (global, no mapping.json)
- Stylesheets: FigmaStyleVariables, FigmaGeneratedStyles, OtherStyles

**CSS:**
```css
:root {
    --existing-var: #FF0000;  /* Exists in all 3 files */
    --new-var: #00FF00;  /* Doesn't exist anywhere */
}
```

**Result:**
```
Processing FigmaStyleVariables:
  --existing-var: Updated ✅
  --new-var: Added (primary) ✅

Processing FigmaGeneratedStyles:
  --existing-var: Updated ✅
  --new-var: Skipped (not primary) ✅

Processing OtherStyles:
  --existing-var: Updated ✅
  --new-var: Skipped (not primary) ✅
```

### Example 2: Explicit Mapping

**Setup:**
- mapping.json: {"custom-colors": "CustomSheet"}
- custom-colors.css

**CSS:**
```css
:root {
    --custom-1: #111111;
    --custom-2: #222222;
}
```

**Result:**
```
Processing CustomSheet:
  --custom-1: Added (explicit targeting) ✅
  --custom-2: Added (explicit targeting) ✅

Processing FigmaStyleVariables:
  --custom-1: Skipped (not targeted, not primary) ✅
  --custom-2: Skipped (not targeted, not primary) ✅

Processing FigmaGeneratedStyles:
  --custom-1: Skipped (not targeted, not primary) ✅
  --custom-2: Skipped (not targeted, not primary) ✅
```

### Example 3: Mixed Scenario

**Setup:**
- global.css (no mapping)
- specific.css → mapping.json: {"specific": "SpecialStyles"}
- Stylesheets: FigmaStyleVariables, FigmaGeneratedStyles, SpecialStyles

**global.css:**
```css
:root {
    --global-new: #AAAAAA;
}
```

**specific.css:**
```css
:root {
    --specific-new: #BBBBBB;
}
```

**Result:**
```
Processing FigmaStyleVariables:
  --global-new: Added (primary) ✅
  --specific-new: Skipped (not targeted) ✅

Processing FigmaGeneratedStyles:
  --global-new: Skipped (not primary) ✅
  --specific-new: Skipped (not targeted) ✅

Processing SpecialStyles:
  --global-new: Skipped (not primary) ✅
  --specific-new: Added (explicit targeting) ✅
```

---

## Benefits

✅ **No More Spam:** New variables/selectors don't pollute every file

✅ **Convenient Defaults:** Small changes "just work" (go to primary stylesheet)

✅ **Explicit Control:** mapping.json for organized multi-file scenarios

✅ **Backward Compatible:** Existing variable updates work exactly as before

✅ **Clear Logging:** Always know where things are added or skipped

✅ **Flexible:** Configure primary stylesheets per project

---

## Future Enhancements

### Potential Improvements:

1. **Global Selector Registry**
   - Pre-scan all stylesheets
   - Detect when selectors exist in other files
   - Warn: "`.green` already exists in FigmaStyleVariables, updating there instead"

2. **Smart Update Mode**
   - If selector exists in another file, update it there
   - Don't create duplicates across files

3. **CLI Commands**
   - `fm-skin-builder css-scan`: Show which stylesheets contain which selectors
   - `fm-skin-builder css-find .classname`: Find where a selector is defined

4. **Configuration Validation**
   - Warn if primary_variable_stylesheet doesn't exist in bundle
   - Suggest available stylesheet names

---

## Testing

**Manual Testing Scenarios:**

1. ✅ Add new variable (no mapping) → Should go to FigmaStyleVariables only
2. ✅ Add new variable (with mapping) → Should go to mapped stylesheet
3. ✅ Modify existing variable → Should update all files
4. ✅ Add new selector → Should go to FigmaGeneratedStyles only
5. ✅ Configure custom primary → Should respect configuration
6. ✅ Check logging → Should clearly show add vs skip decisions

**Automated Tests:**
- Existing tests pass (optional parameters with defaults)
- New tests needed for smart placement logic (future work)

---

## Breaking Changes

### What Changed:

**Phase 3.1 & 3.2 behavior for NEW content:**
- **Old:** Add to every stylesheet
- **New:** Add only to targeted or primary stylesheet

**NOT changed:**
- Updating existing variables (still global)
- Updating existing selectors (still works)

### Who's Affected:

**NOT affected:**
- Users who only modify existing variables ✅
- Users who don't use Phase 3 (no new content) ✅

**Affected:**
- Users who add new variables globally
- Users who expect new content in every file

**Fix:** Use mapping.json or accept new default behavior

---

## Summary

**Problem Solved:** No more spamming new variables/selectors to every stylesheet

**Solution:** Hybrid explicit targeting + smart primary stylesheet defaults

**Result:** Clean, organized, user-friendly CSS handling that scales from quick edits to complex multi-file projects
