## Components

- context
	- `BundleContext` owns UnityPy lifecycle (load/save/dispose, optional backup) and exposes dirty tracking via `save_modified()`.
	- `PatchReport` captures change metrics (assets touched, variables patched, texture swaps, dry-run summaries) for CLI/GUI surfaces.

- services
	- `CssPatchService` wraps the `CssPatcher` class and provides an `apply(bundle_ctx, candidate_assets)` method for orchestration layers.
	- `TextureSwapService` coordinates replacements against a loaded bundle, folding counts into a shared `PatchReport` while deferring file writes to the context.

- css_sources
	- Collects CSS variables, selector overrides, and targeting hints from a skin directory.

- scan_cache
	- Manages cached bundle indices (`*.index.json`) and candidate asset discovery.

- bundle_paths
	- Infers Football Manager bundle locations across supported platforms when users do not pass `--bundle`.

- texture_utils
	- Provides replacement stem collection, name mapping, texture prefilter logic, and helpers that feed `TextureSwapService`.

- css_patcher
	- Hosts the core `CssPatcher` implementation plus `PipelineOptions` and `SkinPatchPipeline`, which compose CSS + texture services, scan cache helpers, and bundle saving in a single flow.

- bundle_inspector
	- Scans bundle(s), builds an index of variables/selectors/usages, and optionally exports `.uss` files for reference/diffing.

- cache / skin_config
	- Validates `config.json` and caches parsed models under `.cache/skins/<skin>/<hash>.json`.

- CLI
	- `patch` drives `SkinPatchPipeline`, exposing dry-run, debug export, backup, and caching flags directly to end-users.
	- `scan` remains a power tool for exploring mappings; optional for day-to-day patching.

## Data flow (patch)

```
skin directory
  ├─ collect CSS vars / selector overrides
  ├─ build CssPatchService + TextureSwapService
  └─ for each bundle → BundleContext.load()
        ├─ CssPatchService.apply(...)
        ├─ TextureSwapService.apply(...)
        └─ BundleContext.save_modified(...)
             ↳ PatchReport aggregations drive CLI output (or GUI in future)
```

Dry-run goes through the same discovery and patch calculations; `BundleContext` never writes because `PatchReport.dry_run` stays true.

## Design principles

- Keep orchestration thin: services own UnityPy mutations, the pipeline coordinates only sequencing and reporting.
- Preserve backwards compatibility via `run_patch` shim while encouraging new consumers to use `SkinPatchPipeline` directly.
- Maintain optional scanning/caching to enable faster iterations without mandating precomputed indexes.
