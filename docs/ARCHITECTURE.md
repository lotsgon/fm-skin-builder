## Components

- context
	- `BundleContext` owns UnityPy lifecycle (load/save/dispose, optional backup) and exposes dirty tracking via `save_modified()`.
	- `PatchReport` captures change metrics (assets touched, variables patched, texture swaps, dry-run summaries) for CLI/GUI surfaces.

- services
	- `CssPatchService` wraps the legacy `CssPatcher` class and provides an `apply(bundle_ctx, candidate_assets)` method for orchestration layers.
	- `TextureSwapService` coordinates replacements against a loaded bundle, folding counts into a shared `PatchReport` while deferring file writes to the context.

- css_patcher
	- Still hosts parser/debug helpers plus the core `CssPatcher` implementation.
	- Adds `PipelineOptions` and `SkinPatchPipeline` to compose CSS + texture services, scan cache hints, and bundle saving in a single flow.

- bundle_inspector
	- Scans bundle(s), builds an index of variables/selectors/usages, and optionally exports `.uss` files for reference/diffing.

- cache / skin_config
	- Validate `config.json` and cache parsed models under `.cache/skins/<skin>/<hash>.json`.

- CLI
	- `patch` calls `SkinPatchPipeline` for a class-first workflow (dry-run, debug export, patch-direct all mapped through `PipelineOptions`).
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
