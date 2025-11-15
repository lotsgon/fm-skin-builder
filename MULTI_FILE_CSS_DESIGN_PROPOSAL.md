# Multi-File CSS Design Proposal

## Current Architecture Analysis

### How It Works Now
1. **CSS Collection** (`css_sources.py`)
   - Scans CSS/USS files from a directory
   - Supports `mapping.json` to map CSS files → Unity stylesheet names
   - Three levels of overrides:
     - **Global**: Applied to all stylesheets
     - **Asset-specific** (via mapping.json): Applied to specific named stylesheets
     - **File stem matching**: Automatically matches `FigmaStyleVariables.uss` → `FigmaStyleVariables` stylesheet

2. **Stylesheet Processing** (`css_patcher.py`)
   - Iterates through all MonoBehaviour objects with `colors`/`strings` (StyleSheets)
   - Each stylesheet has `m_Name` attribute (e.g., "FigmaStyleVariables", "FigmaGeneratedStyles", etc.)
   - Gets effective overrides by merging: global + asset-specific + file stem
   - Processes each stylesheet independently

3. **Phase 3 Augmentation**
   - Phase 3.1: Adds CSS variables that don't exist in the stylesheet
   - Phase 3.2: Adds selectors that don't exist in the stylesheet
   - **Problem**: "Doesn't exist" is checked PER FILE, not globally

### Issues Identified

1. **Cross-File Blindness**: When processing stylesheet A, we can't see what's in stylesheet B
2. **Duplicate Selector Addition**: Phase 3 might add `.green` to FigmaGeneratedStyles even though it exists in FigmaStyleVariables
3. **No Conflict Detection**: System doesn't warn when same selector exists in multiple files
4. **User Confusion**: Users think in terms of "one CSS file" but Unity has many USS files
5. **Naming Issues**: Logs might be confusing about which stylesheet is being modified

---

## Proposed Solutions

### **Solution 1: Global Selector Registry (Recommended)**
**Concept**: Build a registry of ALL selectors across ALL stylesheets before Phase 3

#### How It Works
```python
# Before Phase 3, scan all stylesheets and build registry
global_selector_registry = {
    ".green": ["FigmaStyleVariables", "FigmaGeneratedStyles"],  # Exists in 2 files
    ".button": ["FigmaGeneratedStyles"],  # Exists in 1 file
    "--primary-color": ["FigmaStyleVariables"],  # Variable in 1 file
}

# Phase 3.2: Check global registry before adding
if selector not in existing_selector_texts and selector not in global_selector_registry:
    # Only add if truly globally new
    add_selector_to_stylesheet(...)
```

#### Advantages
✅ Prevents duplicate selectors across files
✅ Minimal code changes (one pass before Phase 3)
✅ Can provide warnings: "`.green` already exists in FigmaStyleVariables, skipping..."
✅ Users see cleaner output without duplication

#### Disadvantages
⚠️ Doesn't handle intentional overrides (maybe `.green` SHOULD be in both files)
⚠️ Need to decide policy: skip duplicates? warn? allow with flag?

#### Implementation Complexity
🟢 **Low** - Add one pre-scan pass, update Phase 3 logic

---

### **Solution 2: CSS File → Stylesheet Targeting with Smart Defaults**
**Concept**: Improve mapping.json to be more intuitive with intelligent defaults

#### How It Works
```json
// mapping.json
{
  "global.css": "*",  // Apply to ALL stylesheets
  "colours.css": ["FigmaStyleVariables", "FigmaGeneratedStyles"],  // Apply to specific stylesheets
  "layout.css": "FigmaGeneratedStyles",  // Apply to single stylesheet
  "overrides.css": {
    "stylesheets": ["FigmaGeneratedStyles"],
    "mode": "merge"  // or "replace"
  }
}
```

**Smart Defaults**:
- If no mapping.json: All CSS is global (current behavior)
- Auto-detect: `FigmaStyleVariables.css` → `FigmaStyleVariables` stylesheet (by stem name)
- Special keyword: `"*"` = all stylesheets

#### Advantages
✅ User-friendly: Explicit file → stylesheet mapping
✅ Supports both global and file-specific CSS
✅ Clear intent: "This CSS goes here"
✅ Backward compatible (existing mapping.json still works)

#### Disadvantages
⚠️ Requires users to understand Unity's multi-file structure
⚠️ More configuration required for complex scenarios

#### Implementation Complexity
🟡 **Medium** - Extend mapping parser, update documentation

---

### **Solution 3: Virtual Unified CSS with Auto-Distribution**
**Concept**: Users write ONE CSS file, system distributes to correct USS files automatically

#### How It Works
```css
/* skin.css - User writes ONE file */

/* Variables automatically go to FigmaStyleVariables (or root stylesheet) */
:root {
    --primary-color: #1976d2;
    --secondary-color: #424242;
}

/* Selectors automatically distributed based on "hints" */
.green { color: green; }  /* System detects: already in FigmaStyleVariables, update there */
.new-class { color: red; } /* System detects: doesn't exist, add to FigmaGeneratedStyles */

/* Or explicit targeting with comments */
/* @stylesheet: FigmaStyleVariables */
.button-primary { background: var(--primary-color); }

/* @stylesheet: FigmaGeneratedStyles */
.layout-container { display: flex; }
```

**Distribution Logic**:
1. Scan all USS files to find existing selectors/variables
2. For each CSS rule:
   - If selector exists in USS file X → update X
   - If new selector → add to "primary" USS file (configurable, default: FigmaGeneratedStyles)
   - If explicit `@stylesheet` comment → use that file
3. Variables go to root stylesheet or FigmaStyleVariables by default

#### Advantages
✅ **User Experience**: Users think in normal CSS terms
✅ **Automatic**: System handles Unity complexity behind the scenes
✅ **Smart**: Updates existing selectors where they live
✅ **Flexible**: Support explicit targeting when needed

#### Disadvantages
⚠️ Complex implementation (multi-pass, cross-file analysis)
⚠️ Magic behavior might surprise users
⚠️ Need clear documentation about distribution rules

#### Implementation Complexity
🔴 **High** - Multi-pass processing, new CSS parser, extensive testing

---

### **Solution 4: Catalogue-Aware CSS Processing**
**Concept**: Leverage the asset catalogue to inform CSS processing

#### How It Works
Since we already extract CSS classes and variables into the catalogue, use that data:

```python
# During CSS extraction (catalogue phase)
catalogue = {
    "css_classes": [
        {"name": ".green", "stylesheet": "FigmaStyleVariables", "bundle": "ui.bundle"},
        {"name": ".button", "stylesheet": "FigmaGeneratedStyles", "bundle": "ui.bundle"},
    ],
    "css_variables": [
        {"name": "--primary-color", "stylesheet": "FigmaStyleVariables", ...},
    ]
}

# During CSS patching
# 1. Load catalogue to know what exists where
# 2. For each override, find existing location
if ".green" in user_css:
    existing_location = catalogue.find_selector(".green")  # Returns "FigmaStyleVariables"
    patch_stylesheet(existing_location, ".green", user_css[".green"])
else:
    # Doesn't exist anywhere, add to target stylesheet
    patch_stylesheet(target_stylesheet, ".green", user_css[".green"])
```

#### Advantages
✅ Leverages existing catalogue infrastructure
✅ Knows exact location of every selector/variable
✅ Can show users: "Updated `.green` in FigmaStyleVariables (line 42)"
✅ Enables powerful queries: "Where is this selector defined?"

#### Disadvantages
⚠️ Requires catalogue to be up-to-date
⚠️ Coupling between catalogue and patching systems
⚠️ Need to handle case where catalogue doesn't exist yet

#### Implementation Complexity
🟡 **Medium** - Integration with catalogue system, new query APIs

---

## Recommended Approach: Hybrid Solution (1 + 2 + 4)

Combine the best parts of multiple solutions:

### Phase 1: Global Registry (Solution 1)
- ✅ Quick win: Prevents duplicate selector additions
- ✅ Add pre-scan pass before Phase 3
- ✅ Log warnings when selectors exist elsewhere

### Phase 2: Enhanced Mapping (Solution 2)
- ✅ Improve mapping.json with smart defaults
- ✅ Add `"*"` wildcard for global CSS
- ✅ Better documentation and examples

### Phase 3: Catalogue Integration (Solution 4)
- ✅ Use catalogue to inform patching decisions
- ✅ Enable "smart patching" that updates existing selectors where they live
- ✅ Provide visibility: "This selector lives in file X"

### Phase 4 (Optional): Virtual Unified CSS (Solution 3)
- Future enhancement for advanced users
- Allows single-file CSS workflow
- Can be opt-in feature

---

## Implementation Roadmap

### Immediate (Fix Current Issue)
1. ✅ Fix NameError with `unmatched_selectors` (DONE)
2. Add global selector registry before Phase 3
3. Update Phase 3.2 to check global registry
4. Add logging: "Selector `.green` already exists in FigmaStyleVariables, skipping"

### Short-term (Better UX)
1. Enhance mapping.json parser to support wildcards
2. Add configuration option for "primary stylesheet" (default target for new selectors)
3. Improve logging to always show stylesheet name clearly
4. Document multi-file CSS best practices

### Medium-term (Smart Patching)
1. Integrate catalogue with CSS patcher
2. Add "smart mode": Update selectors where they exist, add new ones to primary stylesheet
3. Add CLI flag: `--css-mode=smart|global|explicit`
4. Add conflict detection and reporting

### Long-term (Advanced Features)
1. Virtual unified CSS with auto-distribution
2. CSS diff tool: Show what changed across all stylesheets
3. CSS optimizer: Consolidate duplicate selectors
4. Visual tool: See which stylesheet contains which selectors

---

## Configuration Examples

### Example 1: Simple Project (Everything Global)
```bash
# No mapping.json needed
# All CSS in colours.css applied to all stylesheets
skin/
  colours.css
```

### Example 2: Explicit Mapping
```json
// mapping.json
{
  "global": "*",  // global.css → all stylesheets
  "colours": "FigmaStyleVariables",  // colours.css → FigmaStyleVariables only
  "layout": "FigmaGeneratedStyles"  // layout.css → FigmaGeneratedStyles only
}
```

### Example 3: Smart Mode (Future)
```bash
# CLI command
fm-skin-builder patch --css-mode=smart --primary-stylesheet=FigmaGeneratedStyles
```

---

## Questions for Decision

1. **Policy for Duplicate Selectors**
   - Skip silently?
   - Skip with warning?
   - Allow duplicates but log?
   - Make it configurable?

   **Recommendation**: Skip with INFO log by default, add `--allow-duplicate-selectors` flag

2. **Default Target for New Selectors**
   - Always global (apply to all)?
   - Always FigmaGeneratedStyles (common base)?
   - Configurable via CLI/config?

   **Recommendation**: Configurable, default to FigmaGeneratedStyles

3. **Catalogue Dependency**
   - Should CSS patcher require catalogue?
   - Should it work standalone?

   **Recommendation**: Catalogue is optional enhancement, patcher works standalone

4. **Migration Path**
   - How to handle existing skins?
   - Backward compatibility requirements?

   **Recommendation**: Fully backward compatible, new features opt-in

---

## Summary

**Immediate Action**: Implement Solution 1 (Global Registry) to fix the duplicate selector issue.

**Recommended Long-term**: Hybrid approach combining global registry, enhanced mapping, and catalogue integration.

**User-Facing Goal**: Hide Unity's multi-file complexity, provide CSS-like experience with intelligent defaults and explicit control when needed.
