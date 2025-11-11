# FM Skin Builder: Frontend-Backend Architecture Analysis

## Executive Summary

The FM Skin Builder uses a **Tauri-based architecture** that bridges a TypeScript/React frontend with a Python backend. The communication follows an **asynchronous event-based pattern** where the frontend receives real-time log updates, progress information, and completion events from the Python backend as the process runs.

### Key Characteristics:
- **Asynchronous, event-based execution**: Frontend receives real-time log updates from the Python backend as the process runs
- **Real-time streaming**: Logs and progress are streamed and displayed live in the UI during process execution
- **Task cancellation support**: Users can stop running builds mid-execution
- **Single-threaded pipelines**: Sequential bundle processing
- **Optimization focus**: Content hashing and deduplication for catalogues
- **Platform-specific handling**: Special subprocess isolation on macOS for texture extraction

---

## 1. Call Chain: Button Click to Python Execution

### 1.1 Frontend (React/TypeScript)

**File**: `/home/user/fm-skin-builder/frontend/src/App.tsx`

```
User clicks "Preview Build" or "Build Bundles"
    ↓
runTask(mode: 'preview' | 'build')
    ├─ buildConfig(mode) → TaskConfig
    │  └─ Sets skinPath, bundlesPath, debugExport, dryRun (true for preview)
    │
    ├─ invoke('run_python_task', { config })
    │  └─ Invokes async Tauri command (non-blocking)
    │
    └─ Event listeners receive real-time updates:
       ├─ 'build_log': Individual log messages as they're produced
       ├─ 'build_progress': Progress updates (current/total bundles)
       └─ 'build_complete': Final success/failure status
    │
    └─ Response handling:
       ├─ Split stdout by newlines
       ├─ Split stderr by newlines  
       └─ Append to logs with timestamps
```

**Key UI Elements**:
- Build tab: Folder selectors, switches, action buttons
- Logs tab: Auto-scrolling terminal view
- Status indicator: Shows "Backend Ready" or "Frontend Preview"

### 1.2 Tauri Backend (Rust)

**File**: `/home/user/fm-skin-builder/frontend/src-tauri/src/main.rs`

**Command Definitions**:
```rust
#[tauri::command]
fn run_python_task(app_handle: AppHandle, config: TaskConfig) -> Result<CommandResult, String>

#[tauri::command]
fn select_folder(dialog_title: Option<String>, initial_path: Option<String>) -> Option<String>
```

**Python Command Construction**:
```rust
fn python_command() → PathBuf
  ├─ Check: .venv/bin/python3 (Unix)
  ├─ Check: .venv/Scripts/python.exe (Windows)
  └─ Fallback: system python3 or python.exe

fn build_cli_args(config: &TaskConfig) → Vec<String>
  └─ Build args: ["patch", skin_path, "--bundle", bundles_path, ...]
```

**Execution Flow**:
```rust
let mut command = Command::new(python_command());

if debug_assertions {
    cmd.arg("-m").arg("fm_skin_builder")  // Development mode
} else {
    // Production mode: use bundled binary
    let backend_binary = app_handle.path().resolve(
        if cfg!(windows) { "resources/backend/fm_skin_builder.exe" } 
        else { "resources/backend/fm_skin_builder" },
        BaseDirectory::Resource
    );
    command = Command::new(backend_binary)
}

command.args(&cli_args);
let output = command.output()?;  // BLOCKING CALL

return CommandResult {
    stdout: String::from_utf8_lossy(&output.stdout),
    stderr: String::from_utf8_lossy(&output.stderr),
    status: output.status.code().unwrap_or(-1)
}
```

### 1.3 Python Backend CLI

**File**: `/home/user/fm-skin-builder/fm_skin_builder/cli/main.py`

**Entry Point**: `__main__.py` → `cli/main.py:main()`

```
Args: ["patch", skin_path, "--bundle", bundles_path, "--dry-run"]
  ↓
ArgumentParser.parse_args()
  ├─ Matches "patch" subcommand
  ├─ Creates subparser with options: --bundle, --debug-export, --dry-run, etc.
  └─ Calls cmd_patch.run(args)
  
cmd_patch.run(args)
  └─ Creates TaskConfig from args
  └─ Calls run_patch() from core module
```

---

## 2. Build/Preview Pipeline Architecture

### 2.1 High-Level Pipeline (SkinPatchPipeline)

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/css_patcher.py` (line 859)

```
SkinPatchPipeline.run(bundle=None)
  │
  ├─ Phase 1: Collect CSS from Directory
  │  └─ collect_css_from_dir(css_dir)
  │     ├─ Parse *.css files
  │     ├─ Extract CSS variables
  │     ├─ Extract selector overrides
  │     └─ Load targeting hints (optional advanced filtering)
  │
  ├─ Phase 2: Load Skin Config (optional)
  │  └─ load_or_cache_config(css_dir)
  │     ├─ Parse config.json
  │     └─ Extract bundle paths, asset includes
  │
  ├─ Phase 3: Setup Services
  │  ├─ CssPatchService (applies CSS variable patches)
  │  └─ TextureSwapService (replaces textures if configured)
  │
  ├─ Phase 4: Locate Bundle Files
  │  └─ infer_bundle_files(css_dir) OR use --bundle arg
  │     └─ Smart sorting: SpriteAtlas → Atlas → Others
  │
  ├─ Phase 5: Load Scan Cache (optional)
  │  └─ For known skins, load cached bundle indices
  │     ├─ Speeds up candidate discovery
  │     └─ Validates cache by bundle fingerprint (mtime+size)
  │
  ├─ Phase 6: Process Each Bundle
  │  ├─ _process_bundle(bundle_path, services, ...)
  │  │  │
  │  │  ├─ Backup original (if --backup)
  │  │  │
  │  │  ├─ CssPatchService.apply(bundle_context)
  │  │  │  └─ Loads bundle with UnityPy
  │  │  │  └─ Iterates MonoBehaviour stylesheets
  │  │  │  └─ Patches color values in-memory
  │  │  │  └─ Updates CSS properties with new values
  │  │  │
  │  │  ├─ TextureSwapService.apply(bundle_context)
  │  │  │  └─ Replaces icon/background textures if present
  │  │  │
  │  │  └─ BundleContext.save_modified()
  │  │     ├─ If dry_run: skip save
  │  │     └─ Otherwise: serialize modified bundle to output
  │  │
  │  └─ Aggregate PatchReport (changes, asset counts, etc.)
  │
  └─ Phase 7: Return Results
     └─ PipelineResult with summary metrics
```

### 2.2 CSS Patching Engine (CssPatcher)

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/css_patcher.py` (line 75)

**Key Concept**: Transforms CSS variables into Unity color values

```
CssPatcher.patch_bundle(bundle_context, candidate_assets)
  │
  ├─ Load Unity bundle with UnityPy
  │
  ├─ Iterate all MonoBehaviour objects
  │  └─ Filter by stylesheet name (if candidate_assets provided)
  │
  ├─ For each stylesheet:
  │  │
  │  ├─ Get effective overrides (merged global + asset-specific CSS)
  │  │  └─ _effective_overrides(stylesheet_name)
  │  │     ├─ Combine global_vars (all CSS variables)
  │  │     ├─ Combine global_selectors (all selector rules)
  │  │     ├─ Add asset-specific overrides if name matches
  │  │     └─ Return merged CSS context
  │  │
  │  ├─ Check if stylesheet will be patched
  │  │  └─ _will_patch(data, css_vars, selector_overrides)
  │  │     ├─ Check var-based direct property patches
  │  │     ├─ Check root-level variable references
  │  │     ├─ Check strict CSS variable mapping
  │  │     ├─ Check direct literal patches (if --patch-direct)
  │  │     └─ Check selector/property overrides
  │  │
  │  ├─ Export debug originals (if --debug-export and will patch)
  │  │  └─ Save original USS format for inspection
  │  │
  │  └─ Apply patches
  │     └─ _apply_patches_to_stylesheet(...)
  │        ├─ For each CSS variable:
  │        │  └─ Find matching color index in bundle
  │        │  └─ Update RGBA values
  │        │
  │        ├─ For each selector override:
  │        │  └─ Find matching selector in bundle
  │        │  └─ Find matching property
  │        │  └─ Update color value
  │        │
  │        └─ Call data.save() to persist changes
  │
  ├─ Export debug patched files (if requested)
  │
  └─ Return PatchReport
     ├─ assets_modified: Set[str] (stylesheet names)
     ├─ variables_patched: int (count of CSS vars applied)
     ├─ direct_patched: int (count of direct color patches)
     ├─ selector_conflicts: List (multi-asset touches for warnings)
     └─ summary_lines: List[str] (dry-run output)
```

### 2.3 Texture Swapping (TextureSwapService)

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/services.py`

```
TextureSwapService.apply(bundle, skin_dir, out_dir, report)
  │
  ├─ Check if textures should be swapped
  │  └─ Configured icons/backgrounds in skin config
  │
  ├─ Gather texture names from bundle
  │  └─ Via scan cache or fresh scan
  │
  ├─ Find replacement files
  │  ├─ assets/icons/ directory (user-provided icons)
  │  └─ assets/backgrounds/ directory (user-provided backgrounds)
  │
  ├─ For each matching texture:
  │  ├─ Load replacement image
  │  ├─ Embed into bundle
  │  └─ Track in report.texture_replacements
  │
  └─ Handle dynamic sprite rebinds
     └─ For paired bundles (SIImage compatibility)
```

**Optimization**: Early prefiltering skips texture processing if no user-provided replacements

---

## 3. Process Management & Execution Flow

### 3.1 Synchronous Execution Model

```
Tauri Main Thread
  │
  ├─ User initiates action (click "Build Bundles")
  │
  ├─ invoke('run_python_task', config)
  │  │
  │  ├─ Rust handler: run_python_task()
  │  │  │
  │  │  ├─ std::process::Command::new(python_path)
  │  │  │
  │  │  ├─ command.output()
  │  │  │  └─ BLOCKS until process exits
  │  │  │
  │  │  └─ Collects stdout + stderr
  │  │
  │  └─ Returns CommandResult to frontend
  │
  ├─ Frontend appends logs
  │
  └─ UI updates with results
```

**Important**: 
- ❌ No concurrent execution (no threading)
- ❌ No real-time log streaming
- ✅ Simple, reliable design
- ⚠️ UI blocks during build (progress indicator shows it's running)

### 3.2 Windows vs. Unix Process Handling

**File**: `/home/user/fm-skin-builder/frontend/src-tauri/src/main.rs`

**Windows-Specific Handling**:
```rust
// Python path resolution
if cfg!(windows) {
    PathBuf::from(".venv/Scripts/python.exe")
    // or fallback to system "python.exe"
}

// Network path special case
if os.name == 'nt' && (
    bundle_path.startswith('\\\\') ||      // UNC path
    bundle_path[0:1] in 'PQRSTUVWXYZ' ||   // Mapped drive
    'localhost@' in bundle_path             // WebDAV
)
{
    // Read file into memory first (fsspec bug workaround)
    // Then pass bytes to UnityPy
    bundle_data = open(bundle_path, 'rb').read()
    UnityPy.load(bundle_data)  // Load from bytes
}
```

**macOS-Specific Handling**:
```python
# Texture extraction subprocess isolation (macOS only)
if platform.system() == 'Darwin' and texture_format in [28, 29]:  # DXT1, DXT5
    # Use subprocess to prevent segfaults
    from multiprocessing import Process, Queue
    
    process = Process(target=extract_in_subprocess, args=(...))
    process.start()
    process.join(timeout=30)
    
    if process.exitcode != 0:
        # Crashed - skip texture, continue gracefully
        return texture_without_image_data
```

---

## 4. Asset Catalogue Optimization

### 4.1 Catalogue Builder Architecture

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/catalogue/builder.py`

```
CatalogueBuilder.build(bundle_paths)
  │
  ├─ Phase 1: Extract Raw Data
  │  └─ _extract_from_bundles(bundles)
  │     ├─ For each bundle:
  │     │  ├─ Extract CSS (variables + classes)
  │     │  ├─ Extract sprites (raw data only)
  │     │  ├─ Extract textures (raw data only)
  │     │  ├─ Extract fonts
  │     │  └─ gc.collect() after each bundle
  │     │
  │     └─ Store raw data (not fully processed yet)
  │
  ├─ Phase 2: Process Images (Expensive)
  │  └─ _process_images()
  │     ├─ For each sprite/texture:
  │     │  │
  │     │  ├─ compute_hash(image_data)  [SHA256, cheap]
  │     │  │  └─ If hash in _sprite_hash_cache:
  │     │  │     └─ Reuse cached processing results
  │     │  │
  │     │  ├─ If not cached:
  │     │  │  ├─ create_thumbnail(image_data)
  │     │  │  │  └─ Resize large images to 256x256
  │     │  │  │
  │     │  │  └─ extract_dominant_colors(image_data)
  │     │  │     └─ 5 dominant colors via k-means
  │     │  │
  │     │  └─ Store results in cache for next occurrence
  │     │
  │     └─ Track processed vs. deduplicated count
  │
  ├─ Phase 3: Deduplicate Assets
  │  └─ _deduplicate_assets()
  │     └─ deduplicate_by_filename(names)
  │        ├─ Remove size suffixes (_16, _24, _32, @2x, etc.)
  │        └─ Group variants as aliases
  │           Example: icon_player_16 → icon_player (primary)
  │                    icon_player_24, icon_player_32 → aliases
  │
  ├─ Phase 4: Build Search Index
  │  └─ SearchIndexBuilder.build_index(vars, classes, sprites, textures)
  │
  ├─ Phase 5: Create Metadata
  │  └─ CatalogueMetadata with counts and timestamps
  │
  └─ Phase 6: Export to JSON
     └─ CatalogueExporter.export(metadata, assets...)
```

### 4.2 Key Optimizations

**1. Content Hash Caching** (Early Deduplication)
```python
# Hash computation (cheap, O(n) over image bytes)
content_hash = compute_hash(image_data)

# Check cache BEFORE expensive image processing
if content_hash in self._sprite_hash_cache:
    # Reuse cached thumbnail + colors
    cached = self._sprite_hash_cache[content_hash]
    sprite = Sprite(
        thumbnail_path=cached['thumbnail_path'],
        dominant_colors=cached['dominant_colors'],
        ...
    )
    return sprite, was_cached=True

# Not cached - do expensive work
thumbnail_path = create_thumbnail(image_data)  # PIL resize
dominant_colors = extract_dominant_colors(image_data)  # k-means

# Store for next encounter
self._sprite_hash_cache[content_hash] = {
    'thumbnail_path': ...,
    'dominant_colors': ...
}
```

**Effect**: 
- First occurrence of image: Full processing
- Subsequent occurrences (e.g., _1x, _2x, _3x, _4x): Instant cache hit
- Saves image processing time by factor of 4+

**2. Scale Variant Grouping** (Parallel Catalogue)
```
Parallel Job 0: [ui-icons_1x, ui-icons_2x, ui-icons_3x, ui-icons_4x]
  ├─ Extract all 4 variants (raw data)
  ├─ Process first image (expensive)
  ├─ Cache hash → processed data
  ├─ Process remaining 3 variants (instant from cache)
  └─ Export partial catalogue

Parallel Job 1: [textures_1x, textures_2x, ...]
  └─ Same pattern
```

**3. Memory Management**
```python
# After each bundle scan:
gc.collect()  # Force garbage collection to free UnityPy memory

# During image processing:
# - Pre-downsample large images (>2048px) to 2048px
# - Convert to PNG immediately (not stored as PIL Image)
# - Delete temp objects: del img_copy, del buf
```

### 4.3 Content Hasher (SHA256)

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/catalogue/content_hasher.py`

```python
def compute_hash(data: bytes | str) -> str:
    """SHA256 hash for asset deduplication."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def compute_file_hash(file_path: str) -> str:
    """SHA256 with chunked reading for large files."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)  # 8KB chunks
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
```

---

## 5. Logging & Output Handling

### 5.1 Logger Setup

**File**: `/home/user/fm-skin-builder/fm_skin_builder/core/logger.py`

```python
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()  # stdout
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

### 5.2 Log Collection & Display

**Frontend** (`/home/user/fm-skin-builder/frontend/src/App.tsx`):

```typescript
const runTask = async (mode: TaskMode) => {
  try {
    const response = await invoke<CommandResult>('run_python_task', { config });
    
    // Split stdout into lines
    if (response.stdout.trim().length) {
      const lines = response.stdout.trim().split('\n');
      lines.forEach((line) => appendLog(line));
    }
    
    // Split stderr into lines with [STDERR] prefix
    if (response.stderr.trim().length) {
      const lines = response.stderr.trim().split('\n');
      lines.forEach((line) => appendLog(`[STDERR] ${line}`));
    }
    
    // Status summary
    if (response.status === 0) {
      appendLog(`✓ Process completed successfully`);
    } else {
      appendLog(`✗ Process exited with status ${response.status}`);
    }
  } finally {
    setIsRunning(false);
  }
};
```

### 5.3 Output Pipeline

```
Python logging → stderr/stdout
  ↓ (captured by Command::output())
CommandResult { stdout: String, stderr: String, status: i32 }
  ↓ (sent to frontend)
JavaScript handler
  ├─ Split lines
  ├─ Add timestamps
  └─ Append to logs array
  ↓
React component (ScrollArea)
  └─ Auto-scroll to bottom
```

**Important**: All logs appear **after** process completes (no streaming)

---

## 6. Current Performance Bottlenecks

### 6.1 In Build/Preview Pipeline

| Bottleneck | Location | Cause | Solution Potential |
|------------|----------|-------|-------------------|
| Sequential bundle processing | css_patcher.py:967 | for loop, no parallelization | Multiprocessing (high complexity) |
| Full bundle scan without cache | scan_cache.py | Re-scan every time if no cache | Cache hits already implemented |
| Texture extraction on macOS | texture_extractor.py:214-251 | Segfault protection via subprocess | Already optimized (unavoidable) |
| Large image I/O | image_processor.py | Resizing 4K+ images | Pre-downsampling already done |

### 6.2 In Catalogue Building

| Bottleneck | Location | Cause | Solution Potential |
|------------|----------|-------|-------------------|
| Sequential bundle extraction | builder.py:155 | for loop, one at a time | Parallel groups (already done in GHA) |
| Image processing without early cache | builder.py:213 | Wait for all extraction before processing | Hash-based cache (already implemented) |
| Scale variant reprocessing | extractors/texture_extractor.py | Before parallel split | Grouping + hash cache (already done) |

### 6.3 Windows Network Paths

**Issue**: fsspec has bugs with network paths (UNC, mapped drives, WebDAV)

**Solution**: 
```python
# Load file into memory first
with open(bundle_path, 'rb') as f:
    bundle_data = f.read()
# Pass bytes to UnityPy (avoids fsspec)
env = UnityPy.load(bundle_data)
```

---

## 7. Async & Threading Patterns

### 7.1 Current Approaches

**1. macOS Texture Extraction (Process-based)**
```python
# File: core/catalogue/extractors/texture_extractor.py:214-251

from multiprocessing import Process, Queue

# Run extraction in isolated subprocess
process = Process(target=extract_in_subprocess, args=(bundle_path, texture_name, queue))
process.start()
process.join(timeout=30)

# Handle results/crashes gracefully
if process.is_alive():
    process.terminate()  # Timeout
elif process.exitcode != 0:
    # Subprocess crashed (segfault)
    # Continue without image data
```

**Why**: UnityPy texture decoder crashes on certain formats (DXT1, DXT5) on macOS
**Effect**: One problematic image doesn't kill entire catalogue build

**2. Garbage Collection (Memory Management)**
```python
# After each bundle in catalogue extraction:
finally:
    gc.collect()

# This is NOT async - just cleanup between iterations
```

### 7.2 What's NOT Implemented

❌ Async/await (no asyncio)
❌ Threading (no Thread pools)
❌ Concurrent processes for build pipeline
❌ Real-time log streaming
❌ Background jobs in Tauri

### 7.3 Why Not?

1. **Simplicity**: Current design is deterministic and debuggable
2. **Python GIL**: Threading doesn't help CPU-bound work
3. **Process isolation complexity**: Need IPC for results
4. **Frontend readiness**: No WebSocket infrastructure for streaming
5. **Catalogue uses parallel GHA**: Parallelism handled at workflow level, not Python code

---

## 8. Data Structures & Models

### 8.1 TaskConfig (Frontend → Rust → Python)

```typescript
// Frontend (App.tsx)
type TaskConfig = {
  skinPath: string;
  bundlesPath: string;
  debugExport: boolean;
  dryRun: boolean;
};

// Rust (main.rs)
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct TaskConfig {
    skin_path: String,
    bundles_path: String,
    debug_export: bool,
    dry_run: bool,
}

// Python (cli/main.py)
# Converted to argparse arguments:
# ["patch", skin_path, "--bundle", bundles_path, "--dry-run", "--debug-export"]
```

### 8.2 CommandResult (Rust → Frontend)

```rust
#[derive(Serialize)]
struct CommandResult {
    stdout: String,
    stderr: String,
    status: i32,
}
```

### 8.3 Internal Models

**PatchReport**:
```python
@dataclass
class PatchReport:
    bundle_path: Path
    assets_modified: Set[str]
    variables_patched: int
    direct_patched: int
    selector_conflicts: List[Tuple[str, str, int]]
    dry_run: bool
    summary_lines: List[str]
    saved_path: Optional[Path]
    texture_replacements: int
```

**CatalogueMetadata**:
```python
@dataclass
class CatalogueMetadata:
    fm_version: str
    catalogue_version: int
    built_at: datetime
    bundles_scanned: List[str]
    asset_counts: Dict[str, int]
    search_index_built: bool
```

---

## 9. Configuration & Customization

### 9.1 Skin Config Format

**File**: `config.json` in skin directory

```json
{
  "includes": ["assets/icons", "assets/backgrounds"],
  "bundles": "/path/to/bundles",
  "overrides": {
    "stylesheet_name": {
      "--variable-name": "#RRGGBB"
    }
  }
}
```

### 9.2 Targeting Hints (Advanced)

**Files**: `config.hints.json` or `hints.json`

```json
{
  "assets": ["StyleSheet1", "StyleSheet2"],
  "selectors": [".selector1", ".selector2"],
  "selector_props": [
    [".selector1", "property-name"],
    [".selector2", "other-property"]
  ]
}
```

**Purpose**: Limit patching to specific stylesheets/selectors (avoid conflicts)

---

## 10. Error Handling & Resilience

### 10.1 Frontend Error Handling

```typescript
try {
  const response = await invoke<CommandResult>('run_python_task', { config });
  // Process response
} catch (error) {
  appendLog(`✗ Command failed: ${String(error)}`);
  setActiveTab('logs');
}
```

### 10.2 Python Error Handling

**Pattern**: Log and continue on non-critical errors

```python
# Catalogue building
for bundle_path in bundles:
    try:
        css_data = self.css_extractor.extract_from_bundle(bundle_path)
    except Exception as e:
        log.warning(f"Error extracting CSS: {e}")
        # Continue to next bundle

# Texture extraction (macOS)
if process.exitcode != 0:
    log.warning(f"Subprocess crashed for {name}")
    # Return texture without image data
    return {..., "image_data": None}
```

### 10.3 Bundle Context (Lifecycle Management)

```python
class BundleContext:
    def __enter__(self):
        self.load()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        self.dispose()  # Always cleanup

# Usage
with BundleContext(bundle_path) as ctx:
    # Do work
    ctx.save_modified(out_dir)
# Automatic cleanup even if exception
```

---

## 11. Deployment & Distribution

### 11.1 Tauri Build Configuration

**File**: `/home/user/fm-skin-builder/frontend/src-tauri/tauri.conf.json`

```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:5173"
  },
  "bundle": {
    "resources": ["resources/backend"],  // Include Python binary
    "targets": "all"  // Windows, macOS, Linux
  }
}
```

### 11.2 Development vs. Production

**Development** (debug_assertions enabled):
```rust
// Run Python module directly
Command::new(python_command())
    .arg("-m")
    .arg("fm_skin_builder")
    .arg("patch")
    .arg(...)
```

**Production**:
```rust
// Run bundled PyInstaller binary
let backend_binary = app_handle.path()
    .resolve("resources/backend/fm_skin_builder.exe", BaseDirectory::Resource)?;
Command::new(backend_binary)
```

### 11.3 Build Process

1. `npm run build` - TypeScript/React compiled to dist/
2. `tauri build` - Bundles frontend + Python binary
3. Platform-specific packaging (NSIS, DMG, AppImage)

---

## 12. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (React)               │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Build Tab: Folder selectors, Debug switch      │   │
│  │  Logs Tab: Terminal output                       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   │ invoke('run_python_task', config)
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│            Tauri Backend (Rust/src-tauri)              │
│  ┌──────────────────────────────────────────────────┐   │
│  │ run_python_task(config)                          │   │
│  │  ├─ Resolve Python executable                   │   │
│  │  ├─ Build CLI args from config                  │   │
│  │  ├─ std::process::Command::output() [BLOCKING]  │   │
│  │  └─ Return CommandResult (stdout/stderr/status) │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────┘
                   │
         Process stdout/stderr
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│           Python Backend (CLI + Core)                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ cli/main.py: Parse args, route to patch command │   │
│  │                                                  │   │
│  │ SkinPatchPipeline:                              │   │
│  │  ├─ collect_css_from_dir()                      │   │
│  │  ├─ load_scan_cache()  [optional]               │   │
│  │  ├─ For each bundle:                            │   │
│  │  │  ├─ CssPatchService.apply()                  │   │
│  │  │  │  ├─ UnityPy.load(bundle)                  │   │
│  │  │  │  ├─ Iterate stylesheets                   │   │
│  │  │  │  └─ Patch colors                          │   │
│  │  │  ├─ TextureSwapService.apply()               │   │
│  │  │  └─ BundleContext.save_modified()            │   │
│  │  └─ Return PipelineResult                       │   │
│  │                                                  │   │
│  │ CatalogueBuilder (parallel in GHA):             │   │
│  │  ├─ Extract CSS/sprites/textures                │   │
│  │  ├─ Process images (with hash cache)            │   │
│  │  ├─ Deduplicate                                 │   │
│  │  └─ Export JSON                                 │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                   │
      Return stdout/stderr to Tauri
                   │
                   ▼
        Frontend appends to logs,
        displays in UI terminal
```

---

## 13. Summary: Call Chain Complete

```
User clicks "Preview Build"
  ↓
runTask('preview') [React component]
  ├─ config.dryRun = true
  ├─ invoke('run_python_task', { config })
  ↓
run_python_task [Tauri handler]
  ├─ Command::new(python_path)
  ├─ .arg("-m").arg("fm_skin_builder")
  ├─ .args(["patch", skin_path, "--bundle", ..., "--dry-run"])
  ├─ .output() [BLOCKS until process exits]
  ↓
fm_skin_builder.cli.main.main()
  ├─ Parse args
  ├─ routes to cmd_patch.run()
  ↓
cmd_patch.run(args)
  └─ run_patch(css_dir, out_dir, ..., dry_run=True)
  ↓
SkinPatchPipeline.run()
  ├─ collect_css_from_dir()
  ├─ For each bundle:
  │  ├─ CssPatchService.apply() → patches colors in memory
  │  ├─ TextureSwapService.apply() → no-op (no textures to swap)
  │  └─ save_modified(dry_run=True) → skips file writes
  ├─ Log all changes to stdout
  └─ Exit with code 0
  ↓
CommandResult { stdout: "[INFO] ...", stderr: "", status: 0 }
  ↓
Frontend handler
  ├─ Split stdout by '\n'
  ├─ appendLog(line) for each line
  ├─ Timestamp each log entry
  └─ Render in terminal with auto-scroll
  ↓
User sees: "Preview Build - Changes without writing files"
```

---

## 14. Recommendations for Extensions

### 14.1 Real-time Log Streaming (Next Priority)

**Current**: All logs after process completes

**Proposed**:
1. Use Tauri's `invoke_listener` for subprocess
2. Pipe stderr → event channel
3. Frontend listens to event stream
4. Display logs in real-time

**Complexity**: Medium (requires Tauri event loop changes)

### 14.2 Parallel Build Pipeline

**Current**: Sequential bundle processing

**Proposed**:
1. Use Python `multiprocessing.Pool`
2. Process N bundles in parallel
3. Aggregate reports

**Complexity**: High (complex error handling, GIL effects, IPC)

### 14.3 Incremental Caching

**Current**: Scan cache for bundle indices

**Proposed**:
1. Cache processed bundles by hash
2. Skip re-patching unchanged bundles
3. Useful for iterative development

**Complexity**: Medium (cache invalidation logic)

### 14.4 Progress Tracking

**Current**: No progress indication during build

**Proposed**:
1. Report completion percentage
2. Estimate time remaining
3. Per-bundle progress

**Complexity**: Medium (requires async/event infrastructure)

---

## File Reference Quick Index

| Component | File | Key Classes/Functions |
|-----------|------|----------------------|
| Frontend | src/App.tsx | App(), runTask(), invoke() |
| Tauri Backend | frontend/src-tauri/src/main.rs | run_python_task(), select_folder() |
| CLI Entry | fm_skin_builder/cli/main.py | main(), entrypoint() |
| Patch Command | fm_skin_builder/cli/commands/patch.py | run() |
| Build Pipeline | fm_skin_builder/core/css_patcher.py | SkinPatchPipeline, CssPatcher, run_patch() |
| CSS Service | fm_skin_builder/core/services.py | CssPatchService, TextureSwapService |
| Context | fm_skin_builder/core/context.py | BundleContext, PatchReport |
| Logger | fm_skin_builder/core/logger.py | get_logger() |
| Catalogue | fm_skin_builder/core/catalogue/builder.py | CatalogueBuilder |
| Content Hash | fm_skin_builder/core/catalogue/content_hasher.py | compute_hash() |
| Deduplicator | fm_skin_builder/core/catalogue/deduplicator.py | deduplicate_by_filename() |
| Texture Extract | fm_skin_builder/core/catalogue/extractors/texture_extractor.py | TextureExtractor, macOS subprocess |

