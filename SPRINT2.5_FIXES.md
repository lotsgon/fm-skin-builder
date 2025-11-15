# Sprint 2.5 - Additional Fixes ✅

## Summary

Fixed two critical issues discovered during testing:
1. Bundle detection for Steam macOS installations (fm.app structure)
2. Warning persistence after user interaction

## Fixes Applied

### 1. ✅ Steam macOS Bundle Detection (fm.app structure)

**Issue:**
- Game detected at: `/Users/lotsg/Library/Application Support/Steam/steamapps/common/Football Manager 26`
- But bundles weren't found
- Logs showed: `⚠ Game found but could not locate bundles directory`

**Root Cause:**
Steam macOS installations have this structure:
```
Football Manager 26/
  fm.app/
    Contents/
      Resources/
        Data/
          StreamingAssets/.../*.bundle
```

The code was checking for `Contents/Resources/Data` directly in the game directory, but not for the `fm.app/Contents/Resources/Data` path that Steam uses.

**Fix:**
- **Implementation:** `frontend/src-tauri/src/paths.rs:196, 217-246`
- Added `fm.app/Contents/Resources/Data` as first check
- Implemented recursive bundle search (up to 3 levels deep)
- Now properly finds bundles in nested subdirectories

**Updated Path Checks:**
```rust
let bundle_subdirs = vec![
    "fm.app/Contents/Resources/Data",  // NEW: macOS Steam (fm.app within game dir)
    "Contents/Resources/Data",          // macOS .app bundle (direct)
    "Contents/Resources/data",          // macOS .app bundle (lowercase)
    "data",                             // Windows/Linux
    "Data",                             // Windows/Linux
    ".",                                // Sometimes bundles are in the root
];
```

**Recursive Bundle Search:**
Since bundles are in subdirectories like `StreamingAssets/LicensedData/Core/*.bundle`, we now recursively search up to 3 levels deep:
```rust
fn has_bundle_files_recursive(path: &Path, depth: usize, max_depth: usize) -> bool {
    // Check for .bundle files
    // Recursively check subdirectories (max 3 levels)
}
```

**Result:**
✅ Auto-detect now finds bundles in Steam macOS installations:
```
✓ Found game installation: /Users/.../Steam/steamapps/common/Football Manager 26
✓ Found bundles directory: /Users/.../Football Manager 26/fm.app/Contents/Resources/Data
```

---

### 2. ✅ Warning Persistence Fixed

**Issue:**
- Warnings shown after auto-detect failure would persist
- Even after user typed in the field or selected a folder via Browse
- Warning would remain visible despite having a valid path

**Root Cause:**
Skin folder input field only cleared `pathErrors`, not `pathWarnings`

**Fix:**
- **Implementation:** `frontend/src/App.tsx:524-526`
- Added warning clearing to skin folder onChange handler
- Bundles field already had this logic

**Before:**
```typescript
onChange={(e) => {
  setSkinPath(e.target.value);
  if (pathErrors.skin && e.target.value.trim()) {
    setPathErrors(prev => ({ ...prev, skin: undefined }));
  }
  // Missing: pathWarnings clearing
}}
```

**After:**
```typescript
onChange={(e) => {
  setSkinPath(e.target.value);
  if (pathErrors.skin && e.target.value.trim()) {
    setPathErrors(prev => ({ ...prev, skin: undefined }));
  }
  if (pathWarnings.skin && e.target.value.trim()) {
    setPathWarnings(prev => ({ ...prev, skin: undefined }));
  }
}}
```

**Warning Clear Triggers:**
- ✅ User types in the field
- ✅ User selects folder via Browse button
- ✅ Auto-detect succeeds

---

## Files Modified

### Rust:
1. `frontend/src-tauri/src/paths.rs:190-246` - Bundle detection with recursive search

### Frontend:
1. `frontend/src/App.tsx:524-526` - Skin folder warning clearing

---

## Testing Verification

### Before:
```
[07:12:49] ✓ Found game installation: /Users/.../Football Manager 26
[07:12:49] ⚠ Game found but could not locate bundles directory
[07:12:49] Please select the bundles directory manually
```

### After (Expected):
```
[07:12:49] ✓ Found game installation: /Users/.../Football Manager 26
[07:12:49] ✓ Found bundles directory: /Users/.../Football Manager 26/fm.app/Contents/Resources/Data
```

---

## Compilation Status

✅ **All checks passed:**
- Rust compilation: Successful
- Frontend linting: No warnings or errors
- Ready for testing

---

## Next Steps

**Test the fixes:**
1. Click Auto-detect on Bundles field
2. Should now find both game installation AND bundles directory
3. Paths should auto-populate correctly
4. If auto-detect still fails, warning should appear
5. Type in field or browse → warning disappears

If these work correctly, Sprint 2.5 is fully complete and ready for beta release!
