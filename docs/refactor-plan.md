# Core Refactor Plan (Class-First Architecture)

## Progress Snapshot (Nov 2025)
- ✅ Phase 1 foundations: `BundleContext` and `PatchReport` shipped, legacy call sites wrapped.
- ✅ Phase 2 (partial): `CssPatchService` and `TextureSwapService` in place; `SkinPatchPipeline` introduced for orchestration.
- ⏳ Upcoming: Bundle scan service extraction, expanded test suites, and documentation refresh (CONTEXT, CLI guidance).

## Goals
- Make `src/core` reusable from CLI, GUI, or future automation by exposing cohesive class-based APIs.
- Preserve current behaviours (bundle patching, scanning, texture swapping) with zero regression for existing command-line flows.
- Improve testability by isolating UnityPy side-effects behind well-defined classes, enabling mocks/fakes in unit tests.
- Prepare documentation (`docs/ARCHITECTURE.md`, future `CONTEXT.md`) to present the new class hierarchy as the entry point for contributors.

## Current State Inventory

| Module | Primary Responsibilities | Notes |
| --- | --- | --- |
| `css_patcher.py` | Collect CSS variables, patch Unity StyleSheet assets, orchestrate run_patch. | Mix of helper functions and `CssPatcher` class, procedural orchestration via `run_patch`.
| `bundle_inspector.py` | Procedural bundle scanner producing JSON/USS dumps. | No class encapsulation; returns dicts and writes files directly.
| `textures.py` | Procedural texture replacement with large helper surface. | Core logic in functions; state passed via parameters.
| `bundle_manager.py` | Early attempt at bundle abstraction. | Not integrated with rest of core; logic overlaps with `CssPatcher`.
| `patcher.py` | Legacy entry point wrapping BundleManager. | Likely deprecated by CLI; needs alignment.
| `cache.py`, `skin_config.py`, `logger.py` | Focused utilities; already class-based or functionally pure. |

## Target Class Architecture

### Foundational Layer
- `BundleContext`: owns a UnityPy environment, handles lazy loading, saving, disposal, and optional backup logic.
- `PatchReport`: immutable summary describing changes (assets touched, replacements). Used for CLI/GUI status surfaces.
- `SkinProject`: encapsulates skin directory, cached config, targeting hints, and asset lookups.

### Domain Services
- `CssPatchService`: wraps existing `CssPatcher` logic, exposing `apply(bundle: BundleContext, targeting: PatchTargeting) -> PatchReport`.
- `TextureSwapService`: encapsulates texture and sprite overlay operations; coordinates name mapping and replacements.
- `BundleScanService`: class wrapper for scanning with configurables (USS export, conflict detection).
- `ScanCache`: optional adapter to `cache.py` for persistence of scan indexes.

### Orchestration
- `SkinPatchPipeline`: composes services to run full patch flow (CSS + textures + reporting). Accepts options analogous to CLI flags.
- `PipelineOptions`: dataclass capturing patch settings (dry-run, debug export, patch_direct, etc.).
- CLI/GUI adapters become thin wrappers that instantiate `SkinProject`, `SkinPatchPipeline`, call orchestration, and present `PatchReport` data.

## Migration Strategy

1. **Foundation Prep**
   - Introduce `BundleContext`, `PatchReport`, and helper dataclasses in new module (`src/core/context.py` or similar).
   - Provide transitional adapters so existing code (e.g., `run_patch`) can wrap these classes without immediate behaviour change.

2. **Service Extraction**
   - Refactor `CssPatcher` into `CssPatchService` (retaining functionality) and migrate `run_patch` to delegate to the service + context.
   - Extract `TextureSwapService` from `textures.py`; ensure vector sprite support stays intact.
   - Wrap `bundle_inspector` logic into `BundleScanService`; maintain CLI compatibility by exporting through the new class.

3. **Pipeline Introduction**
   - Create `SkinPatchPipeline` to coordinate CSS, textures, caching, and debug exports.
   - Update CLI (`cli/commands/patch.py`) and any GUI entry points to consume the pipeline.
   - Deprecate procedural modules (`patcher.py`, legacy functions) with compatibility shims/logging.

4. **Testing Upgrade**
   - Add unit tests for services with UnityPy fakes/mocks or fixture bundles (dry-run focus) under `tests/core/`.
   - Cover pipeline integration (dry-run and real patch scenarios using small synthetic bundles).
   - Ensure existing tests continue to pass; add regression coverage for texture atlas + vector sprite paths.

5. **Documentation Refresh**
   - Update `docs/ARCHITECTURE.md` to describe class-first layout and usage examples.
   - Author/refresh `CONTEXT.md` (if missing) with dependency diagram, data flow, and extension points.
   - Document migration notes for downstream consumers (e.g., other tools importing procedural functions).

## Risk & Mitigation
- **UnityPy side-effects**: Encapsulate load/save within `BundleContext` to ensure resources freed; add context-manager support.
- **Backward compatibility**: Provide wrapper functions (e.g., keep `run_patch` delegating to pipeline) until downstream callers migrated.
- **Testing complexity**: Start with dry-run mode to avoid writing large bundles during tests; leverage fixtures in `backups/` or synthetic assets.

## Deliverables per Phase

| Phase | Key Outputs |
| --- | --- |
| 1 | `BundleContext`, `PatchReport`, updated `run_patch` wiring (no behaviour change). ✅ |
| 2 | `CssPatchService`, `TextureSwapService`, `BundleScanService` classes + updated modules. *(Services shipped; scan service pending)* |
| 3 | `SkinPatchPipeline`, CLI refactor, legacy shims with deprecation notices. *(Pipeline shipped; CLI update next)* |
| 4 | Test suite expansion (`tests/core/test_css_service.py`, etc.). |
| 5 | Updated docs (`docs/ARCHITECTURE.md`, new `CONTEXT.md`). |

## Open Questions
- How do we handle concurrent patching of multiple bundles (threading requirements)?
- Should texture/vector replacements be toggleable per service in the pipeline options?
- Do we need to expose asynchronous variants for future GUI progress reporting?

## Next Steps
1. Draft `BundleContext` and `PatchReport` APIs and gather feedback.
2. Spike `CssPatchService` class refactor in a feature branch to validate ergonomics.
3. Align CLI expectations with pipeline return values (success/failure codes, summary output).
## Upcoming Priorities

1. **Stabilise the pipeline contract**
   - Add regression tests around `run_patch` covering inferred bundles, explicit bundle paths (file and directory), dry-run, debug export, and backup flows.
   - Assert the new `PipelineResult` fields (counts, summary lines, dry-run metrics) so future changes cannot silently break the CLI surface.
   - Smoke-test the CLI against representative skins to confirm real-world logging and backups still behave as expected.
2. **Trim the mega-modules**
   - Extract pure helpers from `src/core/css_patcher.py` into dedicated modules for parsing/selector utilities, scan-cache helpers, and pipeline orchestration.
   - Apply the same treatment to `src/core/textures.py`, separating discovery/filter logic from mutation routines.
   - As we carve pieces out, wrap them with unit tests to raise coverage incrementally.
3. **Prepare richer front ends**
   - On top of the refactored modules, design a progress callback/event interface that the pipeline can invoke per bundle/service step (sync first, async-ready later).
   - Document requirements for a GUI/async adapter (progress phases, error handling, cancellation) before building the concrete implementation.
4. **Optional follow-ups once the above is stable**
   - Explore an optional JSON/structured output mode for the CLI to support automation.
   - Revisit asynchronous execution when the progress contract is in place and the core modules are modular.

## Packaging & Runtime Decisions (Nov 2025)

- **Output layout**: mirror Football Manager’s structure under the user’s documents folder (e.g., `~/Documents/FM Skin Builder/skins/<skin>/packaged`). The generated bundles live inside `packaged/`; the schema and build tooling must ignore that directory when re-building a skin.
- **Global cache**: move `.cache` into an app-data style location (platform specific) so cached indexes survive repository moves. Only indexes and metadata live here—per-skin packaged bundles remain in each skin’s `packaged/` directory.
- **Bundle discovery**: auto-detect the FM26 StreamingAssets root per OS and use it as the default bundle source. Provide overrides plus tooling to clear/reset cache globally or per skin to handle game patches or user preference changes.
- **Cache semantics**: caching records bundle fingerprints and asset listings, not binary payloads. This keeps cache useful when users tweak existing skins (e.g., recolour + icon change) without blocking them with stale contents; changes in upstream bundles invalidate the cache via fingerprint mismatch.
