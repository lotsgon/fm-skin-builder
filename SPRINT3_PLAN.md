# Sprint 3: Settings UI & Path Persistence - Plan

## Overview

Add persistent settings, cache management, and a Settings UI to improve user experience and prepare for auto-updater (Sprint 4).

## Goals

1. **Path Persistence** - Save user's folder selections between app sessions
2. **Settings UI** - Dedicated interface for managing app preferences
3. **Cache Management** - View cache size, clear cache, show location
4. **Beta Opt-in** - Preference for auto-updater (preparation for Sprint 4)
5. **App Info** - Display version, paths, system info

---

## Features to Implement

### 1. Path Persistence

**Problem:** Users have to re-select folders every time they open the app.

**Solution:** Save paths to Tauri's built-in store, load on startup.

**Implementation:**
- Use `@tauri-apps/plugin-store` for persistent storage
- Save `skinPath` and `bundlesPath` whenever they change
- Load saved paths on app initialization
- Provide "Reset to Default" option

**User Flow:**
1. User selects skin folder and bundles directory
2. Paths automatically saved to store
3. Next app launch: Paths pre-populated
4. User can click "Reset" in Settings to clear saved paths

---

### 2. Settings UI

**Design:** New "Settings" tab in the main interface (next to Build and Logs)

**Layout:**
```
┌─────────────────────────────────────┐
│ Settings                            │
├─────────────────────────────────────┤
│                                     │
│ 📁 Paths                            │
│   • Skin Folder: [path] [Clear]    │
│   • Bundles Dir: [path] [Clear]    │
│   • Default Skins: [path]           │
│   • Cache Dir: [path] [Open]        │
│                                     │
│ 🗄️ Cache                            │
│   • Size: 124 MB                    │
│   • Location: [path]                │
│   [Clear Cache]                     │
│                                     │
│ 🔄 Updates                          │
│   ☐ Enable beta updates             │
│   • Current: v0.2.0-45 (beta)       │
│   [Check for Updates]               │
│                                     │
│ ℹ️ About                            │
│   • Version: 0.2.0-45               │
│   • Platform: macOS (arm64)         │
│   • Python: [backend version]       │
│                                     │
└─────────────────────────────────────┘
```

**Sections:**

1. **Paths Section**
   - Display saved paths
   - Quick clear/reset buttons
   - Show cache directory
   - "Open in Finder/Explorer" button for cache

2. **Cache Section**
   - Show cache size (MB/GB)
   - Show cache location
   - Clear cache button with confirmation
   - Last cleared timestamp

3. **Updates Section** (for Sprint 4)
   - Beta opt-in toggle
   - Current version display
   - Manual "Check for Updates" button
   - Update channel (Stable/Beta)

4. **About Section**
   - App version
   - Platform info (OS, arch)
   - Backend (Python) version
   - Links to docs, GitHub, report issues

---

### 3. Cache Management Commands

**New Rust Commands:**

```rust
#[tauri::command]
fn get_cache_size(app_handle: AppHandle) -> Result<u64, String>
// Returns cache directory size in bytes

#[tauri::command]
fn clear_cache(app_handle: AppHandle) -> Result<String, String>
// Deletes all files in cache directory

#[tauri::command]
fn open_cache_dir(app_handle: AppHandle) -> Result<(), String>
// Opens cache directory in system file browser
```

**Implementation:**
- Recursively calculate cache directory size
- Delete all files/subdirectories in cache (preserve structure)
- Use platform-specific "open" command (Finder, Explorer, etc.)

---

### 4. Path Persistence Implementation

**Tauri Store Setup:**

```typescript
// Load store
const store = await load('settings.json', { autoSave: true });

// Save paths
await store.set('skinPath', '/path/to/skin');
await store.set('bundlesPath', '/path/to/bundles');
await store.save();

// Load paths on startup
const savedSkinPath = await store.get<string>('skinPath');
const savedBundlesPath = await store.get<string>('bundlesPath');
```

**Auto-Save Strategy:**
- Save immediately when paths change (debounced)
- Load on app mount (before runtime initialization)
- Provide manual "Save" button in Settings
- Provide "Reset to Default" button

---

### 5. Beta Opt-In Preference

**Purpose:** Allow users to opt-in to beta updates (for Sprint 4 auto-updater)

**Storage:**
```typescript
await store.set('updateChannel', 'beta' | 'stable');
await store.set('checkForUpdates', true | false);
```

**UI:**
- Toggle switch: "Enable beta updates"
- Warning text: "Beta versions may be unstable"
- Default: Stable channel
- Separate toggle: "Automatically check for updates"

---

## User Stories

### As a user...

1. **I want my folder selections to persist**
   - So I don't have to re-select them every time I open the app
   - Acceptance: Paths remembered between app sessions

2. **I want to clear the cache**
   - So I can free up disk space or fix issues
   - Acceptance: Cache cleared with one click, size shown

3. **I want to see where my cache is stored**
   - So I can manually inspect or manage it
   - Acceptance: Cache path shown, "Open" button works

4. **I want to opt-in to beta updates**
   - So I can get new features faster
   - Acceptance: Toggle saves preference, used in Sprint 4

5. **I want to see app information**
   - So I know which version I'm running
   - Acceptance: Version, platform, backend info displayed

---

## Technical Implementation

### Dependencies to Add

```toml
# Cargo.toml
[dependencies]
tauri-plugin-store = "2.0"
tauri-plugin-shell = "2.0"  # For opening cache dir
```

```json
// package.json
{
  "dependencies": {
    "@tauri-apps/plugin-store": "^2.0.0",
    "@tauri-apps/plugin-shell": "^2.0.0"
  }
}
```

### File Structure

```
frontend/src-tauri/src/
  ├── cache.rs         # NEW: Cache management commands
  └── settings.rs      # NEW: Settings commands (if needed)

frontend/src/
  ├── components/
  │   └── Settings.tsx # NEW: Settings UI component
  └── hooks/
      └── useStore.ts  # NEW: Store hook for persistence
```

---

## Implementation Steps

### Phase 1: Backend (Rust)
1. Add Tauri store plugin to dependencies
2. Create `cache.rs` module:
   - `get_cache_size()` command
   - `clear_cache()` command
   - `open_cache_dir()` command
3. Add commands to main.rs
4. Test cache operations

### Phase 2: Store Integration (TypeScript)
1. Add store plugin to frontend dependencies
2. Create `useStore.ts` hook
3. Implement save/load path logic
4. Test persistence across app restarts

### Phase 3: Settings UI (React)
1. Create `Settings.tsx` component
2. Add Settings tab to main layout
3. Implement Paths section (display, clear)
4. Implement Cache section (size, clear, open)
5. Implement Updates section (beta toggle)
6. Implement About section (version, platform)
7. Style with existing UI components

### Phase 4: Integration & Testing
1. Wire up Settings to store
2. Wire up cache commands
3. Test path persistence
4. Test cache management
5. Test beta opt-in toggle
6. Cross-platform testing (if possible)

---

## Success Criteria

- [ ] Paths persist between app sessions
- [ ] Cache size displayed correctly
- [ ] Clear cache works and shows confirmation
- [ ] Open cache directory works on all platforms
- [ ] Beta opt-in toggle saves preference
- [ ] Settings UI is intuitive and accessible
- [ ] No regressions in existing functionality
- [ ] All code compiles without warnings

---

## Non-Goals (Save for Later)

- ❌ Actual auto-updater implementation (Sprint 4)
- ❌ Theme customization (future)
- ❌ Keyboard shortcuts (future)
- ❌ Advanced cache options (selective clear)
- ❌ Import/export settings (future)

---

## Risks & Considerations

1. **Store Plugin Compatibility**
   - Risk: Tauri store plugin may have breaking changes
   - Mitigation: Use stable version, test thoroughly

2. **Cache Size Calculation Performance**
   - Risk: Large caches may take time to calculate size
   - Mitigation: Run calculation async, show loading state

3. **Path Validation**
   - Risk: Saved paths may become invalid (moved/deleted)
   - Mitigation: Validate on load, show warning if invalid

4. **Cross-Platform Testing**
   - Risk: Cache operations may behave differently per platform
   - Mitigation: Test on multiple platforms, use platform guards

---

## Next Steps

After approval:
1. Add dependencies (Tauri plugins)
2. Create cache management commands
3. Set up store integration
4. Build Settings UI
5. Test everything
6. Document in SPRINT3_COMPLETE.md

Ready to proceed? 🚀
