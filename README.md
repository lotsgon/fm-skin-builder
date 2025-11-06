# Football Manager 2026 Skin Builder

CSS-first tooling for Football Manager bundles. Drop in CSS/USS overrides and the builder takes care of scanning, patching, and texture swaps.

## Prerequisites

- Python 3.10+ (3.11 recommended)
- `pip install -r requirements.txt`
- Unity bundles extracted locally (or let the tool infer them from a Football Manager install)

## CLI Overview

Run all commands through `python -m src.cli.main ...` from the repository root.

Available commands:

- `patch` — apply CSS/USS overrides (and optional texture swaps) to one or more bundles
- `scan` — build an index of selectors, variables, and assets for discovery or diffing
- `build`, `extract`, `verify`, `swap` — reserved for future workflows (stubs today)

Use `python -m src.cli.main <command> --help` for CLI reference.

## Patch Workflow

1. Prepare a skin folder (see `skins/test_skin` for structure).
   - `config.json` with at least `schema_version` and `target_bundle`
   - CSS/USS overrides in `colours/*.uss` or alongside `config.json`
   - Optional `assets/icons` and `assets/backgrounds` for texture swaps
2. Run the patch command:

```bash
python -m src.cli.main patch skins/your_skin --out build/skins
```

- Without `--bundle`, the CLI infers bundles from `config.json` or installed FM paths.
- Point `--bundle` at a specific `.bundle` file or a directory of bundles to override auto-discovery.

Common flags:

- `--dry-run` — report changes without writing bundles (summaries land in stdout)
- `--debug-export` — write original and patched `.uss`/JSON to `<out>/debug_uss`
- `--patch-direct` — replace literal color values in addition to CSS variables
- `--backup` — create `.bak` files alongside each input bundle
- `--no-scan-cache` — skip cached scan indices
- `--refresh-scan-cache` — force new scan indices before patching

Patching output:

- Modified bundles are written to `--out` with an `_modified.bundle` suffix.
- Texture swaps (icons/backgrounds) reuse the same out directory and report counts in the CLI summary.
- Dry runs leave the filesystem untouched but emit `Summary:` lines per bundle.

## Scan Workflow

Use scan when exploring bundle contents or precomputing indices for faster patches:

```bash
python -m src.cli.main scan --bundle bundles --out build/scan --export-uss
```

- Accepts a single `.bundle` or a directory tree.
- Produces `<out>/<bundle>.index.json` and, when `--export-uss` is set, `.uss` files for each stylesheet asset.
- Scan caches live under `.cache/skins/<skin>/<bundle>.index.json` and are reused automatically by the patch command unless disabled.

## Environment Notes

- Set `FM_HARD_EXIT=0` to disable the hard exit safeguard if you prefer normal interpreter shutdown.
- The tool respects targeting hints (`hints.txt`) to limit patch scope—see `docs/recipes/targeting-hints.md`.
- Texture name mappings (`assets/*/mapping.json`) steer the new texture prefilter and swap pipeline.

## Documentation

- `docs/CLI_GUIDE.md` — step-by-step CLI usage and troubleshooting
- `docs/README.md` — documentation index and quick start
- `docs/SKIN_FORMAT.md` — skin layout and configuration schema
- `docs/ARCHITECTURE.md` — module breakdown and data flow
- `docs/recipes/` — focused guides for common tasks

### Need Help?

- Check the recipes for targeted workflows (`dry-run`, `scan-and-cache`, etc.).
- Run with `--debug-export` to inspect generated `.uss` files when CSS changes are not appearing.
- Re-run with `--refresh-scan-cache` if bundles changed upstream or cached indices look stale.
