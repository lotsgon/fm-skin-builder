# Implementation Plan - FM Skin Builder

This document outlines the bugs to fix and features to implement, organized by priority.

## 🐛 Critical Bugs (Fix First)

### 1. Version Numbers Fixed ✅
**Status:** FIXED
**Issue:** Builds showing `0.1.0-36` instead of `0.2.0-36`
**Root Cause:** GitHub Actions checkout was doing shallow clone without tags/history
**Solution:** Added `fetch-depth: 0` and `fetch-tags: true` to checkout step
**File:** `.github/workflows/build-app.yml:222-225`

### 2. Stop Button Not Working
**Status:** TODO
**Issue:** Stop button doesn't actually stop the running task
**Root Cause:** Child process is moved out of mutex immediately after spawn (main.rs:498) for waiting. When stop is called, mutex is empty.
**Solution:** Keep child in mutex while running, use Arc<Mutex> properly
**Files:** `frontend/src-tauri/src/main.rs:492-502, 606-633`

**Implementation:**
- Don't `take()` the child from mutex immediately
- Wait for child in a separate task that checks cancellation
- Stop function sets a cancellation flag and kills the process

### 3. Progress Bar Not Moving
**Status:** TODO
**Issue:** Progress bar doesn't update during build process
**Root Cause:** Need to investigate `parse_progress()` function - likely Python isn't outputting progress in expected format
**Solution:**
1. Check Python backend progress output format
2. Verify Rust `parse_progress()` parsing logic
3. Ensure frontend receives and displays progress events correctly

**Files:**
- `frontend/src-tauri/src/main.rs` (parse_progress function)
- Python backend progress emission
- `frontend/src/App.tsx:616-625` (progress display)

### 4. Python Startup Delay
**Status:** ACKNOWLEDGED
**Issue:** Noticeable delay when first starting Python process
**Root Cause:** PyInstaller binary cold start + process spawn overhead
**Mitigation:** Already shows "cold start may take a moment" message
**Potential Improvements:**
- Show animated loading indicator
- Pre-warm the process on app startup (background task)
- Better progress feedback during initialization

## 🎯 High Priority Features

### 5. Auto-Updater (Beta Only)
**Status:** PLANNED
**Scope:** Implement Tauri auto-updater with beta opt-in

**Requirements:**
- ✅ Opt-in to beta channel in settings
- ✅ Auto-receive stable updates (default behavior)
- ❌ Optional: Roll back to previous beta versions (defer to future)

**Implementation Steps:**

#### Phase 1: Settings Infrastructure
1. Create settings storage system
   - Use Tauri's store plugin or localStorage
   - Settings schema: `{ betaChannel: boolean, autoUpdate: boolean }`
   - Default: `betaChannel: false, autoUpdate: true`

2. Create Settings UI Component
   - New Settings page/modal
   - Toggle for "Enable Beta Updates"
   - Toggle for "Auto-update" (on by default)
   - "Check for Updates" button
   - Display current version and available updates

#### Phase 2: Auto-Updater Integration
1. Generate Tauri signing keys
   ```bash
   cd frontend
   npm run tauri signer generate
   ```

2. Set GitHub Secrets
   - `TAURI_SIGNING_PRIVATE_KEY`
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

3. Enable updater in `tauri.conf.json`
   ```json
   "updater": {
     "active": true,
     "endpoints": [
       "https://release.fmskinbuilder.com/{{target}}/{{arch}}/{{current_version}}"
     ],
     "pubkey": "YOUR_PUBLIC_KEY"
   }
   ```

4. Implement updater logic
   - Check for updates on app startup
   - Respect beta channel setting
   - Show update dialog with release notes
   - Download and install updates
   - Restart app after update

**Endpoint Logic:**
- Beta enabled: Check `beta/latest.json`
- Beta disabled: Check `releases/latest.json`
- Both contain platform-specific update info

**Files to Create/Modify:**
- `frontend/src/store/settings.ts` - Settings store
- `frontend/src/components/Settings.tsx` - Settings UI
- `frontend/src/components/UpdateDialog.tsx` - Update notification
- `frontend/src/hooks/useUpdater.ts` - Updater logic
- `frontend/src-tauri/tauri.conf.json` - Enable updater
- Update scripts to generate proper `latest.json` format

**Deferred:** Beta version rollback (complex, requires version history UI)

### 6. Settings UI
**Status:** PLANNED (needed for auto-updater)

**Options:**
1. **Settings Icon in Header** (Recommended)
   - Add gear/cog icon to top-right header
   - Opens modal/slide-out panel
   - Quick access, doesn't leave main page

2. **File Menu Option**
   - Add "Settings" to application menu
   - Opens dedicated settings page
   - More traditional desktop app approach

**Settings Categories:**
```
General
├── Beta Channel (toggle)
├── Auto-Update (toggle)
└── Check for Updates (button)

Paths
├── Game Installation (auto-detect button)
├── Bundles Directory (browse/auto-detect)
└── Skins Directory (browse)

Cache
├── Cache Location (display path)
├── Cache Size (display)
└── Clear Cache (button)

About
├── Version
├── Documentation Link
└── GitHub/Website Links
```

### 7. Game/Bundle Auto-Detection
**Status:** PLANNED

**Reference:** [FMMLoader-26 game_detection.rs](https://github.com/justinlevinedotme/FMMLoader-26/blob/main/src-tauri/src/game_detection.rs)

**Requirements:**
- Detect FM installation directory
- Locate Unity bundles within installation
- Set bundles path automatically
- Fall back to manual selection if not found

**Platform-Specific Paths:**
- **Windows:** `C:\Program Files (x86)\Steam\steamapps\common\Football Manager 2026\`
- **macOS:** `/Applications/Football Manager 2026.app/`  or  `~/Library/Application Support/Steam/steamapps/common/Football Manager 2026/`
- **Linux:** `~/.steam/steam/steamapps/common/Football Manager 2026/`

**Implementation:**
1. Create `frontend/src-tauri/src/game_detection.rs`
2. Port logic from FMMLoader-26
3. Add Tauri command `detect_game_installation()`
4. UI: "Auto-detect" button next to bundles path
5. Show detection results or fallback to manual

**Validation:**
- Verify bundles directory contains `.bundle` files
- Check for specific bundle names (e.g., `panels.bundle`)

### 8. Skins Directory Management
**Status:** PLANNED

**Requirements:**
- Create `FM Skin Builder` folder in user's Documents
- Auto-create on first launch
- Leave skin path empty by default
- Require user to select before building
- Offer "Open Skins Folder" button

**Platform-Specific Documents Paths:**
- **Windows:** `%USERPROFILE%\Documents\FM Skin Builder\`
- **macOS:** `~/Documents/FM Skin Builder/`
- **Linux:** `~/Documents/FM Skin Builder/`

**Implementation:**
1. Create skins directory on app startup
2. Add validation: require non-empty skin path before build/preview
3. Show helpful message if empty: "Please select a skin folder or create one in [path]"
4. Add "Open Skins Folder" button that opens in file explorer

### 9. Cache Directory Relocation
**Status:** PLANNED

**Current:** `.cache/` in project root (bad)
**Target:** Platform-appropriate app data directory

**Platform-Specific Cache Paths:**
- **Windows:** `%LOCALAPPDATA%\FM Skin Builder\cache\`
- **macOS:** `~/Library/Caches/com.fmskinbuilder.app/`
- **Linux:** `~/.cache/fm-skin-builder/`

**Implementation:**
1. Update Python backend to use new cache location
2. Use Tauri's `app_cache_dir()` API
3. Pass cache path to Python via environment variable or CLI arg
4. Migrate existing cache if found
5. Add "Clear Cache" button in settings
   - Shows cache size
   - Confirms before clearing
   - Displays success message

**Files to Modify:**
- Python cache initialization code
- `frontend/src-tauri/src/main.rs` - Pass cache dir to Python
- Settings UI - Add cache management

### 10. Documentation Link
**Status:** SIMPLE

**Implementation:**
- Add `?` icon to top-right header (next to theme toggle)
- Opens `https://fmskinbuilder.com` in browser
- Use Tauri's `shell::open()` API

**Code:**
```tsx
<Button
  variant="ghost"
  size="icon"
  onClick={() => window.open('https://fmskinbuilder.com', '_blank')}
  title="Documentation"
>
  <HelpCircle className="h-5 w-5" />
</Button>
```

## 📋 Implementation Order

### Sprint 1: Bug Fixes
1. ✅ Version numbers (done)
2. Stop button functionality
3. Progress bar updates
4. (Acknowledge Python startup delay)

### Sprint 2: Path Management
1. Move cache to app data directory
2. Auto-create skins folder in Documents
3. Game installation detection
4. Validate paths before build

### Sprint 3: Settings UI
1. Settings store/persistence
2. Settings modal/page
3. Documentation link
4. Clear cache functionality

### Sprint 4: Auto-Updater (Beta)
1. Generate signing keys
2. Configure updater in tauri.conf.json
3. Implement update check logic
4. Update dialog UI
5. Beta channel toggle
6. Test beta updates end-to-end

### Sprint 5: Polish
1. Better loading states
2. Error handling improvements
3. User feedback messages
4. Documentation updates

## 🚫 Deferred Features

### Beta Version Rollback
**Reason:** Complex feature requiring:
- Version history storage
- Download old versions from R2
- Downgrade logic
- UI for version selection

**Alternative:** Users can manually download old versions from GitHub Releases

## 📝 Notes

### Auto-Updater Architecture

**Stable Channel (Default):**
```
App checks: https://release.fmskinbuilder.com/releases/latest.json
Downloads: Stable releases only
```

**Beta Channel (Opt-in):**
```
App checks: https://release.fmskinbuilder.com/beta/latest.json
Downloads: Beta releases (but can also get stable if newer)
```

**latest.json Structure:**
```json
{
  "version": "0.2.0-123",
  "platforms": {
    "darwin-aarch64": {
      "url": "https://release.fmskinbuilder.com/beta/0.2.0-123/update.app.tar.gz",
      "signature": "...",
      "installers": [
        {
          "url": "https://release.fmskinbuilder.com/beta/0.2.0-123/FM_Skin_Builder_0.2.0-123_aarch64.dmg",
          "format": "dmg",
          "size": 50123456
        }
      ]
    }
  }
}
```

### Settings Storage
Use Tauri's built-in store or localStorage:
- `betaChannel`: boolean (default: false)
- `autoUpdate`: boolean (default: true)
- `gamePath`: string (auto-detected or manual)
- `bundlesPath`: string (auto-detected or manual)
- `skinsPath`: string (manual)
- `lastUpdateCheck`: timestamp

## Ready to Implement?

Once you approve this plan, I can start implementing in the order specified. Each sprint builds on the previous one, ensuring a stable development process.

Which sprint would you like me to start with?
