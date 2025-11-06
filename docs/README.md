## Documentation overview

- Start here: SKIN_FORMAT.md (skin layout, config)
- CLI usage: CLI_GUIDE.md (step-by-step command walkthrough)
- Architecture: ARCHITECTURE.md (how patching works)
- Roadmap: ROADMAP.md
- Developer TODO: TODO.md

### Recipes

Practical guides for common tasks live under recipes/:

- recipes/change-variable.md
- recipes/override-selector.md
- recipes/dry-run.md
- recipes/scan-and-cache.md
- recipes/targeting-hints.md
- recipes/conflict-surfacing.md
- recipes/debug-exports.md

## Quick start

1) Create a skin (see skins/test_skin for an example):
- Put CSS/USS overrides under `colours/*.uss` (or `*.css`/`*.uss` in the skin root)
- Keep a `config.json` with at least `schema_version` and `target_bundle`

2) Patch bundles using your CSS overrides:
- Infer bundle from the skin config
	- python -m src.cli.main patch skins/your_skin --out build
- Or specify a bundle or bundle directory
	- python -m src.cli.main patch skins/your_skin --out build --bundle /path/to/bundles

Auto-detect bundles (optional): If no bundles/ directory exists and no --bundle is provided, the tool will try to find Football Manager 26's StreamingAssets bundles in default install locations (Steam/Epic) on your OS. Example paths:

- Windows (Steam): C:\\Program Files (x86)\\Steam\\steamapps\\common\\Football Manager 26\\fm_Data\\StreamingAssets\\aa\\StandaloneWindows64
- Windows (Epic): C:\\Program Files\\Epic Games\\Football Manager 26\\fm_Data\\StreamingAssets\\aa\\StandaloneWindows64
- macOS (Steam): ~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX
- macOS (Steam, alt): ~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal
- macOS (Epic): ~/Library/Application Support/Epic/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal
- Linux (Steam): ~/.local/share/Steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneLinux64
	- Alt: ~/.steam/steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneLinux64

3) Optional flags:
- `--dry-run` preview changes without writing files
- `--debug-export` export original/patched .uss and JSON for inspection
- `--patch-direct` also patch inlined color literals

Notes:
- Usability first: you only write CSS; no mapping files are required
- Change-aware: no bundles or debug files are written if nothing changes
- Scan is optional (for exploration and diffs), not required for patching

## Scan (optional)

Use scan when you want to explore which variables/selectors occur and where:

- python -m src.cli.main scan --bundle /path/to/bundle_or_dir --out build/scan --export-uss

This produces a `bundle_index.json` plus optional `.uss` exports for browsing/diffing.

## Caching

- Configs are cached under `.cache/skins/<skin>/<hash>.json`
- Scan info may be cached automatically and used transparently for speed (never required). See recipes/scan-and-cache.md.
