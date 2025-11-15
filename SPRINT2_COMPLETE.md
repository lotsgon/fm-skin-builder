# Sprint 2: Path Management - Completed ✅

## Summary

All path management features have been implemented and tested for compilation.

## Features Implemented

### 1. ✅ Cache Directory Relocated

**Previous Behavior:**
- Cache stored in project root: `.cache/skins/`
- User-visible and cluttered workspace

**New Behavior:**
- **Windows:** `%LOCALAPPDATA%\FM Skin Builder\`
- **macOS:** `~/Library/Caches/com.fmskinbuilder.app/`
- **Linux:** `~/.cache/fm-skin-builder/`

**Implementation:**
- **Python:** `fm_skin_builder/core/cache.py:19-33`
  - Added `FM_CACHE_DIR` environment variable support
  - Falls back to old behavior if not set
- **Rust:** `frontend/src-tauri/src/main.rs:321-344`
  - Gets platform-appropriate cache dir using `app_cache_dir()`
  - Creates directory if it doesn't exist
  - Passes to Python via environment variable
  - Logs cache location to console

**Benefits:**
- Hidden from user
- Follows platform conventions
- Persists between runs
- Easy to clear manually if needed

---

### 2. ✅ Skins Folder Auto-Creation

**Feature:**
- Creates `FM Skin Builder` folder in user's Documents on app startup
- Provides default location for user skins
- Auto-populates when user clicks "Search" icon

**Implementation:**
- **Rust Commands:**
  - `get_default_skins_dir()` - Returns Documents/FM Skin Builder path
  - `ensure_skins_dir()` - Creates directory if it doesn't exist
- **App Startup:** `main.rs:830-839`
  - Automatically creates directory on first launch
- **UI:** Search icon button next to Skin Folder input
  - One click to populate with default directory

**Platform Paths:**
- **Windows:** `%USERPROFILE%\Documents\FM Skin Builder\`
- **macOS:** `~/Documents/FM Skin Builder/`
- **Linux:** `~/Documents/FM Skin Builder/`

---

### 3. ✅ Game Installation Auto-Detection

**Feature:**
- Automatically detects Football Manager 2026 installation
- Finds bundles directory within game files
- One-click setup for bundles path

**Implementation:**
- **Rust Commands:**
  - `detect_game_installation()` - Scans common installation paths
  - `find_bundles_in_game_dir(game_dir)` - Locates bundles within game

**Detection Paths:**

**Windows:**
```
C:\Program Files (x86)\Steam\steamapps\common\Football Manager 2026
C:\Program Files\Steam\steamapps\common\Football Manager 2026
```

**macOS:**
```
/Applications/Football Manager 2026.app/Contents/Resources/Data
~/Library/Application Support/Steam/steamapps/common/Football Manager 2026
```

**Linux:**
```
~/.steam/steam/steamapps/common/Football Manager 2026
~/.local/share/Steam/steamapps/common/Football Manager 2026
```

**UI Feedback:**
- ✓ Success: "Found game installation" + "Found bundles directory"
- ⚠ Warning: "Could not detect game installation"
- Logs show detected paths

---

### 4. ✅ Path Validation Before Build

**Feature:**
- Validates paths before running build/preview
- Shows inline error messages with red borders
- Prevents builds with empty paths
- Real-time error clearing when user types

**Validation Rules:**
1. Skin folder must not be empty
2. Bundles directory must not be empty

**UI Indicators:**
- Red border on input fields with errors
- AlertCircle icon + error message below field
- Errors logged to console
- Automatically switches to "Logs" tab on validation failure

**Implementation:**
- `validatePaths()` function checks both fields
- Called before `runTask()` execution
- Errors stored in `pathErrors` state
- Cleared when user modifies the field

---

## UI Improvements

### Path Input Fields

**Before:**
```
[Input Field                    ] [📁]
```

**After:**
```
[Input Field                    ] [🔍] [📁]
              ↓ Empty
[ ⚠ Skin folder is required     ]
```

### Icons Added:
- **🔍 (Search):** Auto-detect/default directory
  - Skin folder: Uses default Documents/FM Skin Builder
  - Bundles: Auto-detects game installation
- **📁 (Folder):** Manual browse
- **⚠ (AlertCircle):** Validation errors

### Placeholders Updated:
- Skin Folder: `"Select your skin folder..."`
- Bundles: `"Select bundles directory..."`
- More descriptive help text

---

## Commands Added

### Frontend Commands (Tauri):

```typescript
// Get default skins directory path
await invoke<string>('get_default_skins_dir');

// Ensure skins directory exists (creates if needed)
await invoke<string>('ensure_skins_dir');

// Get app cache directory path
await invoke<string>('get_cache_dir');

// Auto-detect FM installation
await invoke<string | null>('detect_game_installation');

// Find bundles within game directory
await invoke<string | null>('find_bundles_in_game_dir', { gameDir: string });
```

---

## Files Modified

### Backend (Python):
1. `fm_skin_builder/core/cache.py` - Environment variable support

### Frontend (Rust):
1. `frontend/src-tauri/src/main.rs` - All new commands + setup
2. `frontend/src-tauri/Cargo.toml` - No changes needed

### Frontend (TypeScript/React):
1. `frontend/src/App.tsx` - Validation, auto-detect handlers, UI updates

---

## Testing Checklist

Before next release, verify:

- [ ] Cache directory created in correct platform location
- [ ] Skins folder created in Documents on startup
- [ ] Auto-detect finds FM 2026 installation (if installed)
- [ ] Auto-detect finds bundles directory
- [ ] Search icon populates default skins path
- [ ] Search icon on bundles auto-detects game
- [ ] Validation prevents builds with empty paths
- [ ] Error messages display with red borders
- [ ] Errors clear when user types
- [ ] Manual folder browse still works
- [ ] All platforms compile without errors

---

## User Experience Flow

### First Launch:
1. App starts → Creates `Documents/FM Skin Builder/` folder
2. Skin folder field: Empty with placeholder
3. Bundles field: Empty with placeholder
4. User clicks 🔍 next to Bundles → Auto-detects game
5. User clicks 🔍 next to Skin → Populates default directory
6. User can now build/preview

### Subsequent Launches:
1. Paths remembered from previous session (if using localStorage)
2. Cache persists in platform-appropriate location
3. Quick access to default/detected paths

---

## Next Steps

Sprint 2 is complete! Ready for:
- **Sprint 3:** Settings UI (manage paths, clear cache)
- **Sprint 4:** Auto-Updater (beta opt-in)

Or test these changes with a beta build first!

---

## Technical Notes

### Cache Migration
- Old cache (`.cache/skins/`) will NOT be automatically migrated
- User can manually copy if needed, or let app rebuild cache
- Consider adding migration logic in future sprint if needed

### Game Detection Limitations
- Only detects standard Steam installations
- Non-Steam versions (Epic, GOG) may need manual selection
- Can be extended with additional paths in future

### Path Persistence
- Currently paths reset on app restart (session state only)
- Consider adding localStorage/Tauri store in Sprint 3 (Settings)
