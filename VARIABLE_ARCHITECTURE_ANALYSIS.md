# Unity USS Variable Architecture Analysis

## How Unity USS Variables Actually Work

### Current Code Behavior (fm_skin_builder)

Looking at `css_patcher.py` lines 784-985, here's what happens:

```python
# Phase 1: Convert variable DEFINITIONS to literals (lines 784-839)
# Example: If --primary-color: var(--base-color) in FMColours
# And user provides: --primary-color: #FF0000
# Result: Converts the definition to a literal color in FMColours.colors[X]

# Phase 2: Update color values at shared indices (lines 940-985)
# Example: If --primary-color uses colors[10] in FMColours
# And user provides: --primary-color: #FF0000
# Result: Updates FMColours.colors[10] = #FF0000
```

### The Critical Problem

**Each USS file has its OWN `colors` array!**

```
FMColours.uss:
  strings = ["--primary-color", "--secondary-color", ...]
  colors = [#FF0000, #00FF00, ...]  ← colors[0] = red
  :root { --primary-color: colors[0]; }

inlineStyle.uss:
  strings = ["--primary-color", "--button-bg", ...]
  colors = [#0000FF, #FFFF00, ...]  ← colors[0] = blue (different!)
  .button { color: var(--primary-color); }  ← references colors[5] maybe
```

**Key Insight**: When Unity serializes USS files, each file is INDEPENDENT.
- Changing `--primary-color` definition in FMColours doesn't affect inlineStyle
- Variable references are resolved AT BUILD TIME and stored as color indices
- Each file has its own color palette

### Current Patching Behavior

The code patches EACH FILE INDEPENDENTLY:

```python
for obj in env.objects:  # Each USS file
    data = obj.read()
    name = getattr(data, "m_Name")  # "FMColours", "inlineStyle", etc.

    css_vars_for_asset, selector_overrides_for_asset = self._effective_overrides(name)

    # Patch THIS file's colors array
    self._apply_patches_to_stylesheet(name, data, css_vars_for_asset, ...)
```

So if user changes `--primary-color: #00FF00`:
1. Scans FMColours → finds `--primary-color` → updates FMColours.colors[X]
2. Scans inlineStyle → finds `--primary-color` → updates inlineStyle.colors[Y]
3. Each file gets its own update!

**This means global variables SHOULD work... but only if the variable exists in each file!**

---

## The Problems You Identified

### Problem 1: Adding New Variables to Every File

Current Phase 3.1 behavior:
```python
# Phase 3.1: Add new CSS variables that don't exist in the stylesheet
unmatched_vars = set(css_vars.keys()) - matched_css_vars - existing_var_names
if unmatched_vars:
    self._add_new_css_variables(data, unmatched_vars, css_vars, name)
```

**Issue**: If user adds `--new-color: #FF0000`:
- Gets added to FMColours with FMColours.colors[N]
- Gets added to inlineStyle with inlineStyle.colors[M]
- Gets added to EVERY file independently
- This is wasteful and confusing!

### Problem 2: Where Should New Variables Live?

Options:
1. **Add to every file** (current behavior) ❌ Wasteful, confusing
2. **Add to specific file** (user must specify) ⚠️ Requires configuration
3. **Create new file** (UserVariables.uss) ⚠️ Complex, requires bundle injection
4. **Remove global overrides** (require explicit file targeting) ⚠️ Breaks current UX

### Problem 3: Variable Reference Resolution

Your concern:
> Global colours like --color-linear-scale-20 will only have their value changed in the single file where variables are stored but not throughout all the files its referenced in

**Let me verify this with the code...**

Looking at `_effective_overrides()` (lines 472-498):
```python
def _effective_overrides(self, stylesheet_name: str):
    vars_combined: Dict[str, str] = dict(self.css_data.global_vars)
    selectors_combined: Dict[Tuple[str, str], str] = dict(self.css_data.global_selectors)

    key = stylesheet_name.lower()

    if key in self.css_data.asset_map:
        for overrides in self.css_data.asset_map[key]:
            vars_combined.update(overrides.vars)
            selectors_combined.update(overrides.selectors)

    return vars_combined, selectors_combined
```

**This applies global variables to EVERY file!**

So if user provides `--primary-color: #00FF00` as a global variable:
- FMColours gets `--primary-color: #00FF00` override
- inlineStyle gets `--primary-color: #00FF00` override
- Every file that has `--primary-color` gets updated

**This SHOULD work correctly for existing variables!**

But for NEW variables... they get added to every file (Problem 1).

---

## Proposed Solutions

### Solution A: Smart New Variable Placement (RECOMMENDED)

**Concept**: Don't add new variables globally. Require explicit placement.

```python
# Phase 3.1 becomes smarter
unmatched_vars = set(css_vars.keys()) - matched_css_vars - existing_var_names
if unmatched_vars:
    # DON'T add to this file automatically!
    log.warning(
        f"  [PHASE 3.1] Skipping {len(unmatched_vars)} new variables "
        f"(not found in {name}): {list(unmatched_vars)[:5]}..."
    )
    log.warning(
        "  To add new variables, use file-specific CSS or --primary-stylesheet option"
    )
```

**User workflow for new variables**:
```json
// mapping.json
{
  "new-variables": "FMColours"  // New vars go to FMColours only
}
```

OR

```css
/* new-variables.css */
/* @stylesheet: FMColours */
:root {
    --new-color: #FF0000;
}
```

**Advantages**:
- ✅ No more spamming every file with new variables
- ✅ User has explicit control
- ✅ Clear intent: "This variable lives in FMColours"
- ✅ Existing global variables still work (updated in each file that has them)

**Disadvantages**:
- ⚠️ Breaking change (Phase 3.1 currently adds new variables)
- ⚠️ Requires user configuration for new variables

### Solution B: Primary Stylesheet Pattern

**Concept**: Configure a "primary stylesheet" for new variables/selectors.

```bash
# CLI option
fm-skin-builder patch --primary-stylesheet FMColours
```

OR

```json
// config.json
{
  "primary_stylesheet": "FMColours",
  "fallback_stylesheet": "inlineStyle"
}
```

**Behavior**:
- New variables → add to primary stylesheet (FMColours)
- New selectors → add to fallback stylesheet (inlineStyle)
- Existing variables → update wherever they exist (global behavior)

**Advantages**:
- ✅ Simple configuration
- ✅ Sensible defaults (colors → FMColours, layout → inlineStyle)
- ✅ Backward compatible (default = current behavior if desired)

**Disadvantages**:
- ⚠️ Still adds variables to ONE file, might not be where user wants

### Solution C: Create UserOverrides.uss File

**Concept**: Create a new USS file for ALL user overrides.

```python
# In patch_bundle():
# 1. Identify unmatched variables/selectors
all_unmatched_vars = set()
all_unmatched_selectors = set()

for obj in env.objects:
    # ... collect unmatched from each file ...
    all_unmatched_vars.update(unmatched_vars)
    all_unmatched_selectors.update(unmatched_selectors)

# 2. Create new stylesheet for overrides
if all_unmatched_vars or all_unmatched_selectors:
    user_overrides_data = create_new_stylesheet(
        name="UserOverrides",
        vars=all_unmatched_vars,
        selectors=all_unmatched_selectors
    )
    add_to_bundle(env, user_overrides_data)
```

**Advantages**:
- ✅ Clean separation: FM's files vs user's changes
- ✅ Easy to see what user changed (all in one file)
- ✅ No pollution of existing files

**Disadvantages**:
- 🔴 Complex: Need to create new MonoBehaviour object
- 🔴 Need Unity to load this file (load order, specificity)
- 🔴 Might not work if Unity doesn't recognize the new file

### Solution D: Disable Global New Variables (SIMPLEST)

**Concept**: Remove Phase 3.1 entirely for global variables.

```python
# In _apply_patches_to_stylesheet():
# Phase 3.1: Only add new variables if file-specific
if key in self.css_data.asset_map:  # Only if explicitly mapped to this file
    unmatched_vars = set(css_vars_for_asset.keys()) - matched_css_vars - existing_var_names
    if unmatched_vars:
        self._add_new_css_variables(data, unmatched_vars, css_vars_for_asset, name)
else:
    # Global CSS: Only update existing variables, don't add new ones
    if unmatched_vars:
        log.warning(f"New variables ignored (use file-specific CSS): {unmatched_vars}")
```

**Advantages**:
- ✅ Simplest solution
- ✅ Prevents accidental pollution
- ✅ Forces users to be explicit

**Disadvantages**:
- 🔴 Breaking change
- 🔴 Less convenient for quick experiments

---

## Recommended Approach

### Phase 1: Immediate Fix (Disable Global Phase 3.1)
```python
# Disable adding new variables globally
# Only allow adding variables to explicitly targeted files
```

### Phase 2: Add Primary Stylesheet Configuration
```json
{
  "primary_variable_stylesheet": "FMColours",
  "primary_selector_stylesheet": "inlineStyle"
}
```

### Phase 3: Enhanced Logging
```
⚠️  [PHASE 3.1] Found 5 new variables not in any stylesheet:
    --new-color-1
    --new-color-2
    ...

To add new variables, either:
  1. Add to mapping.json: {"new-vars": "FMColours"}
  2. Use --primary-stylesheet option
  3. Use file-specific CSS with @stylesheet comment
```

---

## Questions for You

1. **Existing Global Variables**: Do they work correctly now?
   - If user changes `--color-linear-scale-20: #NEW_VALUE`
   - Does it update in ALL files that use it?
   - Or only the file where it's defined?

2. **New Variable Policy**:
   - Should we disable global new variables entirely? (Solution D)
   - Or require explicit configuration? (Solution A/B)
   - Or create dedicated file? (Solution C)

3. **Backward Compatibility**:
   - Is it OK to break Phase 3.1 behavior?
   - Current behavior: New variables added to every file
   - New behavior: New variables require explicit placement

4. **Use Case**:
   - What's your typical workflow?
   - Do you often add NEW variables?
   - Or mostly modify existing ones?

---

## My Recommendation

**Implement Solution A + B (Smart Placement + Primary Stylesheet)**:

1. **For existing variables**: Keep current global behavior
   - User changes `--primary-color` → updates in all files that have it ✅

2. **For new variables**: Require explicit placement
   - Default: Add to primary_stylesheet (configurable, default = "FMColours")
   - Override: Use mapping.json or @stylesheet comment
   - Fallback: Warn and skip if no target specified

3. **Logging**:
   - Clear warnings when new variables are skipped
   - Show which files were updated for existing variables
   - Suggest configuration options

This balances:
- ✅ Convenience (existing variables "just work" globally)
- ✅ Control (new variables need explicit placement)
- ✅ Clean output (no spamming every file)
- ✅ Flexibility (multiple ways to specify target)

**What do you think?**
