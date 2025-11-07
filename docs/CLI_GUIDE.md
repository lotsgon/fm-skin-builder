# CLI Guide

This guide walks through the day-to-day commands exposed by `python -m src.cli.main` and how they interact with the refactored pipeline.

## Installing

1. Install Python 3.10 or newer (3.11 recommended).
2. Clone or download this repository.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Ensure you can access the Football Manager bundles you want to patch. You can point the CLI at those bundles directly or rely on automatic detection from your local install.

## Command Reference

Run `python -m src.cli.main --help` for the global overview and `python -m src.cli.main <command> --help` for per-command options.

### Patch

Applies CSS/USS overrides (and optional texture swaps) to one or more Unity bundles.

```bash
python -m src.cli.main patch <css_dir> [--out <output_dir>] [options]
```

Key arguments:

- `<css_dir>` — Skin folder or directory containing `.css`/`.uss` overrides.
- `--out` — Destination for modified bundles. Defaults to `<css_dir>/packages` when omitted.
- `--bundle` — Optional path to a single `.bundle` file or a directory of bundles. When omitted, the tool infers bundles from `config.json` and common Football Manager install paths.

Useful flags:

- `--dry-run` — Calculate and report changes without writing bundles. Summaries appear in stdout and the returned `PatchReport` objects.
- `--patch-direct` — In addition to CSS variables/selectors, patch literal color values inside assets when safe.
- `--debug-export` — Emit original and patched `.uss` / JSON files under `<out>/debug_uss` for inspection.
- `--backup` — Create `*.bak` copies alongside each source bundle before patching.
- `--no-scan-cache` — Ignore cached scan indices even if they exist.
- `--refresh-scan-cache` — Force refresh of scan indices before patching (handy when bundles were updated).

Texture swaps:

- Place replacement images under `assets/icons` or `assets/backgrounds` inside your skin.
- Provide optional `mapping.json`/`map.json` files (either in `assets/` or the specific asset folder) to map replacement stems to bundle asset names.
- The pipeline uses the new texture prefilter helper to skip bundles that do not reference your targets, keeping patch runs fast.

Per-stylesheet overrides:

- Add a `mapping.json` next to your CSS files (skin root or `colours/`).
- Keys can be file names (`FMColours.uss`), stems (`FMColours`), or relative paths (`colours/FMColours.uss`).
- Values can be a single stylesheet name or a list of names, e.g. `"FMColours": ["FMColours", "AttributeColours"]`.
- Mapped files only apply to the listed assets. Files with no mapping stay global, but their overrides will preferentially apply to assets whose names match the file stem.

Outputs:

- Patched bundles keep the original filename (no `_modified` suffix) and are written to the chosen output directory.
- Dry-run runs leave the filesystem untouched.
- Texture replacement counts are reported per bundle and rolled up in the CLI summary.
- Hint filters (`hints.txt` next to `config.json`) restrict processing to listed assets/selectors when supplied.

### Scan

Creates index files that map CSS variables/selectors to the assets that reference them. Also exports `.uss` files when desired.

```bash
python -m src.cli.main scan --bundle <path> --out <output_dir> [--export-uss]
```

- Accepts either a single `.bundle` or a directory containing many bundles.
- Writes `<output_dir>/<bundle>.index.json` plus optional `.uss` exports.
- The patch pipeline automatically reuses these indices for faster runs unless `--no-scan-cache` is passed.

### Other Commands

`build`, `extract`, `verify`, and `swap` are placeholders for upcoming workflows. They currently log stub messages only.

## Typical Patch Flow

1. Prepare your skin folder:
   - `config.json` with at least `schema_version` and `target_bundle` (or `includes` if you want texture swapping).
   - CSS/USS overrides in `colours/` or the root of the skin folder.
   - Optional `assets/icons` and `assets/backgrounds` containing replacement textures plus optional mapping files.

2. Dry run the patch to confirm what would change:

   ```bash
   python -m src.cli.main patch skins/my_skin --dry-run
   ```

   Add `--out build/test` if you want to inspect results outside of the default `<skin>/packages` folder.

3. Inspect the CLI summary or the generated `debug_uss` directory if `--debug-export` was enabled.

4. Remove `--dry-run` to write patched bundles once you are satisfied:

   ```bash
   python -m src.cli.main patch skins/my_skin --backup
   ```

5. Copy the patched bundle files (from `<skin>/packages` unless you overrode `--out`) into Football Manager's `data` override folder per your modding setup.

## Troubleshooting

- **No bundles found** — Provide `--bundle` explicitly or ensure `config.json` lists a `target_bundle`. Automatic detection searches typical Steam/Epic install paths for FM 26.
- **No changes reported** — Validate that your CSS selectors or variables match assets in the target bundle. Run `scan` and consult the generated indices or use `--debug-export` to compare original vs patched stylesheets.
- **Texture swaps skipped** — Ensure the replacement stems or mappings match the bundle asset names. The pipeline logs when the prefilter finds no references; run with `--refresh-scan-cache` if bundles changed since the last scan.
- **Hard exit at completion** — The CLI uses a fast exit to avoid rare C-extension shutdown crashes. Set `FM_HARD_EXIT=0` if you need normal interpreter teardown.
- **Permission errors creating backups** — Pass `--backup` only when the CLI can write alongside the source bundles, or set `FM_SKIN_BACKUP_TS` to control backup filenames.

## Where Things Live

- Scan cache: `.cache/skins/<skin>/<bundle>.index.json`
- Config cache: `.cache/skins/<skin>/<hash>.json`
- Debug exports: `<out>/debug_uss`
- Patched bundles: `<out>/*.bundle`
- Backups (when enabled): alongside the original bundle as `<name>.bundle.<timestamp>.bak`

## Extending the Pipeline

For development details (module layout, services, and orchestration), read `docs/ARCHITECTURE.md` and the inline docstrings in `src/core`. The refactor breaks down responsibilities into small helper modules (`css_sources`, `scan_cache`, `bundle_paths`, `texture_utils`) so new front-ends (CLI/GUI) can consume the pipeline without touching Unity internals directly.
