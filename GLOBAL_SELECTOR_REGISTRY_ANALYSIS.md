# Global Selector Registry - Still Needed?

## Question
With the new smart placement logic, do we still need a global selector registry to prevent cross-file duplicates?

## TL;DR
**YES, we still need it!** Smart placement prevents spam but doesn't prevent cross-file duplicates.

---

## The Scenario

### Current Situation
**Setup:**
- `.green` class exists in FigmaStyleVariables
- User adds global CSS: `.green { color: red; }`
- No mapping.json (global CSS)

### What Happens Now (Smart Placement Only)

```
Processing FigmaStyleVariables:
  - Check: Does .green exist in THIS file? YES
  - Action: Update .green in FigmaStyleVariables ✅

Processing FigmaGeneratedStyles (primary for selectors):
  - Check: Does .green exist in THIS file? NO
  - Check: Is this the primary stylesheet? YES
  - Action: ADD .green to FigmaGeneratedStyles ❌

Result: .green now exists in BOTH files! Duplicate!
```

### The Problem
**Smart placement only prevents spam (adding to ALL files), but doesn't prevent duplicates across SOME files.**

---

## What Global Registry Would Fix

### With Global Registry

**Pre-scan phase:**
```python
# Before any patching, scan all stylesheets
global_selector_registry = {
    ".green": ["FigmaStyleVariables"],
    ".button": ["FigmaGeneratedStyles"],
    ".panel": ["FigmaStyleVariables", "CustomSheet"],  # Already in 2 files
}
```

**Processing FigmaGeneratedStyles:**
```
  - Check: Does .green exist in THIS file? NO
  - Check: Is this the primary stylesheet? YES
  - Check global registry: Does .green exist ANYWHERE? YES (in FigmaStyleVariables)
  - Action: SKIP adding to FigmaGeneratedStyles, log info ✅

  [INFO] Skipping .green for FigmaGeneratedStyles (already exists in FigmaStyleVariables)
```

---

## Two Design Options

### Option 1: Skip Cross-File Duplicates (Conservative)

**Behavior:**
- If selector exists ANYWHERE, only update existing locations
- Never create duplicates across files
- Primary stylesheet rule doesn't override this

**Example:**
```
.green exists in FigmaStyleVariables

User adds: .green { color: red; } (global CSS)

Result:
  - Update FigmaStyleVariables.green ✅
  - Skip FigmaGeneratedStyles (exists elsewhere) ✅
```

**Pros:**
- ✅ Never creates duplicates
- ✅ Clean, predictable behavior
- ✅ Matches user expectation ("update where it is")

**Cons:**
- ⚠️ Can't intentionally add same selector to multiple files
- ⚠️ Might surprise users who want duplicates (rare?)

### Option 2: Warn But Allow (Permissive)

**Behavior:**
- If selector exists elsewhere, add to primary but WARN user
- Allow duplicates but make user aware

**Example:**
```
.green exists in FigmaStyleVariables

User adds: .green { color: red; } (global CSS)

Result:
  - Update FigmaStyleVariables.green ✅
  - Add to FigmaGeneratedStyles WITH WARNING ⚠️

  [WARNING] Adding .green to FigmaGeneratedStyles, but it already exists in FigmaStyleVariables
  [WARNING] This may cause selector conflicts. Consider using explicit targeting.
```

**Pros:**
- ✅ Flexible - allows intentional duplicates
- ✅ User is informed
- ✅ Matches "primary stylesheet" promise

**Cons:**
- ⚠️ Still creates duplicates (might be confusing)
- ⚠️ Users might ignore warnings

### Option 3: Smart Update Mode (Intelligent)

**Behavior:**
- If selector exists elsewhere AND this is primary stylesheet, UPDATE existing instead of adding new
- "Smart" mode that does what user probably wants

**Example:**
```
.green exists in FigmaStyleVariables

User adds: .green { color: red; } (global CSS)

Result:
  - Found .green in FigmaStyleVariables ✅
  - Update FigmaStyleVariables.green ✅
  - Skip FigmaGeneratedStyles (updated at source) ✅

  [INFO] Updated .green in FigmaStyleVariables (existing location)
  [INFO] Skipping .green for FigmaGeneratedStyles (not primary location)
```

**Pros:**
- ✅ Most intelligent behavior
- ✅ Updates selectors where they live
- ✅ No duplicates
- ✅ User-friendly

**Cons:**
- ⚠️ More complex logic
- ⚠️ Might surprise users (expected primary, got different file)
- ⚠️ Need clear logging to explain behavior

---

## Recommended Approach

**Option 3 (Smart Update Mode) with fallback to Option 1**

### Logic:

```python
# Phase 3.2: Smart new selector placement with global registry

# 1. Build global registry (pre-scan)
global_selector_registry = build_selector_registry(all_stylesheets)

# 2. For each stylesheet
for stylesheet in stylesheets:
    unmatched_selectors = calculate_unmatched_selectors(...)

    for (selector, prop) in unmatched_selectors:
        # Check if exists in this file
        if selector in existing_selector_texts:
            update_selector(stylesheet, selector, prop)  # Normal update
            continue

        # Check if exists in other files (global registry)
        if selector in global_selector_registry:
            other_locations = global_selector_registry[selector]

            if is_primary_stylesheet(stylesheet):
                # Primary stylesheet: Update at existing location instead
                log.info(f"Selector {selector} exists in {other_locations[0]}, updating there")
                # Update will happen when processing that other file
                continue
            else:
                # Not primary: Just skip
                log.info(f"Skipping {selector} for {stylesheet} (exists in {other_locations[0]})")
                continue

        # Doesn't exist anywhere, check if should add
        if should_add_selector(stylesheet):
            add_new_selector(stylesheet, selector, prop)
```

### Example Scenarios:

**Scenario 1: Existing selector, no mapping**
```
.green exists in FigmaStyleVariables
User adds: .green { color: red; }

Processing FigmaStyleVariables:
  [INFO] Updated .green in FigmaStyleVariables ✅

Processing FigmaGeneratedStyles (primary):
  [INFO] Skipping .green (already exists in FigmaStyleVariables) ✅
```

**Scenario 2: New selector, no mapping**
```
.new-class doesn't exist anywhere
User adds: .new-class { color: blue; }

Processing FigmaStyleVariables:
  [INFO] Skipping .new-class (not primary) ✅

Processing FigmaGeneratedStyles (primary):
  [INFO] Adding .new-class to FigmaGeneratedStyles (primary, doesn't exist elsewhere) ✅
```

**Scenario 3: Existing selector, explicit targeting**
```
.button exists in FigmaGeneratedStyles
User adds mapping: {"buttons": "CustomSheet"}
buttons.css: .button { color: green; }

Processing FigmaGeneratedStyles:
  [INFO] Updated .button in FigmaGeneratedStyles ✅

Processing CustomSheet (explicit targeting):
  [INFO] Adding .button to CustomSheet (explicit targeting overrides global registry) ✅

Result: .button in both files (explicit user intent)
```

---

## Implementation Plan

### Phase 1: Build Global Registry
```python
def build_global_selector_registry(env) -> Dict[str, List[str]]:
    """Build registry of all selectors across all stylesheets."""
    registry: Dict[str, List[str]] = defaultdict(list)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        data = obj.read()
        if not hasattr(data, "m_ComplexSelectors"):
            continue

        name = getattr(data, "m_Name", "Unknown")
        selectors = extract_all_selectors(data)

        for selector in selectors:
            registry[selector].append(name)

    return registry
```

### Phase 2: Update Phase 3.2 Logic
```python
# In patch_bundle(), before processing stylesheets
self._global_selector_registry = build_global_selector_registry(env)

# In _apply_patches_to_stylesheet(), Phase 3.2
for (selector, prop) in truly_new_selectors:
    # Check global registry
    if selector in self._global_selector_registry:
        existing_locations = self._global_selector_registry[selector]

        if should_add_selectors:  # Primary or explicitly targeted
            log.info(
                f"  [PHASE 3.2] Skipping {selector} for {name} "
                f"(already exists in {existing_locations[0]})"
            )
            continue

    # Proceed with normal addition logic
    ...
```

### Phase 3: Enhanced Logging
```
[PHASE 3.2] Scanning stylesheets for existing selectors...
[PHASE 3.2] Found 142 selectors across 3 stylesheets

Processing FigmaStyleVariables:
  [PHASE 3.2] Updated .green in FigmaStyleVariables

Processing FigmaGeneratedStyles:
  [PHASE 3.2] Skipping .green (already exists in FigmaStyleVariables)
  [PHASE 3.2] Adding .new-button (primary stylesheet, doesn't exist elsewhere)
```

---

## Benefits

✅ **Prevents cross-file duplicates** - No more `.green` in both FigmaStyleVariables and FigmaGeneratedStyles

✅ **Smart behavior** - Updates selectors where they already exist

✅ **Clear logging** - User always knows why selectors are added/skipped/updated

✅ **Explicit override** - Explicit targeting can still create duplicates if user wants

✅ **Minimal performance impact** - One pre-scan pass, O(n) complexity

---

## Decision Needed

**Should we implement the global selector registry?**

**My recommendation: YES**

**Which option:**
- ✅ **Option 3 (Smart Update Mode)** - Most user-friendly
- Fallback to Option 1 for edge cases
- Explicit targeting always wins (user intent)

**When:**
- Can be done as follow-up to smart placement
- Not critical for initial release but highly valuable
- Estimated effort: 2-4 hours implementation + testing

---

## Summary

**Smart Placement (DONE):**
- ✅ Prevents spam (adding to ALL files)
- ✅ Adds to primary or targeted files only

**Global Registry (NEEDED):**
- ✅ Prevents cross-file duplicates
- ✅ Updates selectors at existing locations
- ✅ Provides clear visibility of where selectors live

**Together they solve:**
1. No spam across all files
2. No duplicates across some files
3. Smart updates at existing locations
4. Clear, predictable behavior
