# Football Manager 2026 Skin Builder

CSS-first tooling for Football Manager bundles. Drop in CSS/USS overrides and the builder takes care of scanning, patching, and texture swaps.

## Prerequisites

- Python 3.10+ (3.11 recommended)
- Unity bundles extracted locally (or let the tool infer them from a Football Manager install)
- Run `npm install` in the repo root after cloning—this triggers the bootstrap script which:
  - provisions `.venv/` via `scripts/setup_python_env.sh` (or `scripts/setup_python_env.ps1` on Windows) pinned to Python 3.9.19 for UnityPy
  - installs frontend dependencies (`frontend/node_modules`)
  - wires Husky hooks
- Subsequent `npm run tauri:*` and backend packaging steps automatically reuse the virtualenv.

## Developer Setup

1. **Clone & Bootstrap**
   ```bash
   git clone https://github.com/your-org/fm-skin-builder.git
   cd fm-skin-builder
   npm install
   ```
   This single command:
   - Creates/updates `.venv/` with the pinned Python 3.9.19 interpreter and installs `requirements-dev.txt` (UnityPy, pytest, Ruff, PyInstaller, etc.).
   - Runs `npm install` inside `frontend/` so Vite/Tailwind/React deps are present.
   - Installs Husky hooks (pre-commit + commit-msg) to enforce lint and Conventional Commits.
   - On Windows, a PowerShell dialog may ask for script permissions; run `Set-ExecutionPolicy Bypass -Scope Process -Force` beforehand if needed.

2. **Daily Commands**
   - `npm run tauri:dev` — launches Vite + the Tauri shell using the virtualenv-driven backend.
   - `npm run tauri:dev-local` — same, but rebuilds the PyInstaller binary first.
   - `npm run lint` — runs Ruff, Cargo fmt/clippy, and ESLint (also executed on every commit via Husky).
   - `npm run test:frontend` / `pytest` — targeted test entry points.

3. **Updating Tooling**
   - After Python deps change, rerun `scripts/setup_python_env.sh` (or `.ps1`).
   - After frontend deps change, rerun `npm install` in `frontend/` (bootstrapper detects missing `node_modules`).


## CLI Overview

Run all commands through `python -m fm_skin_builder.cli.main ...` from the repository root.

Available commands:

- `patch` — apply CSS/USS overrides (and optional texture swaps) to one or more bundles
- `scan` — build an index of selectors, variables, and assets for discovery or diffing
- `build`, `extract`, `verify`, `swap` — reserved for future workflows (stubs today)

Use `python -m fm_skin_builder.cli.main <command> --help` for CLI reference.

## Patch Workflow

1. Prepare a skin folder (see `skins/test_skin` for structure).
   - `config.json` with at least `schema_version` and `target_bundle`
   - CSS/USS overrides in `colours/*.uss` or alongside `config.json`
   - Optional `assets/icons` and `assets/backgrounds` for texture swaps
2. Run the patch command:

```bash
python -m fm_skin_builder.cli.main patch skins/your_skin
```

- Without `--bundle`, the CLI infers bundles from `config.json` or installed FM paths.
- Point `--bundle` at a specific `.bundle` file or a directory of bundles to override auto-discovery.
- Omit `--out` to write patched bundles back into `<skin>/packages`; pass `--out <dir>` to use a custom destination.

Common flags:

- `--dry-run` — report changes without writing bundles (summaries land in stdout)
- `--debug-export` — write original and patched `.uss`/JSON to `<out>/debug_uss`
- `--patch-direct` — replace literal color values in addition to CSS variables
- `--backup` — create `.bak` files alongside each input bundle
- `--no-scan-cache` — skip cached scan indices
- `--refresh-scan-cache` — force new scan indices before patching

Patching output:

- Modified bundles keep their original filenames and are written to the chosen output directory (default: `<skin>/packages`).
- Texture swaps (icons/backgrounds) reuse the same out directory and report counts in the CLI summary.
- Dry runs leave the filesystem untouched but emit `Summary:` lines per bundle.

Per-stylesheet overrides:

- Place a `mapping.json` next to your CSS (either in the skin root or `colours/`) to target specific Unity stylesheets.
- Each key corresponds to a CSS file name (with or without extension, relative paths also work). The value lists stylesheet asset names to receive that file's variables/selectors.
- Files without an explicit mapping still apply globally, but the patcher now also falls back to matching assets by CSS filename stem, letting `fm_colours.uss` preferentially apply to `FMColours`.

## Scan Workflow

Use scan when exploring bundle contents or precomputing indices for faster patches:

```bash
python -m fm_skin_builder.cli.main scan --bundle bundles --out build/scan --export-uss
```

- Accepts a single `.bundle` or a directory tree.
- Produces `<out>/<bundle>.index.json` and, when `--export-uss` is set, `.uss` files for each stylesheet asset.
- Scan caches live under `.cache/skins/<skin>/<bundle>.index.json` and are reused automatically by the patch command unless disabled.

## Environment Notes

- Set `FM_HARD_EXIT=0` to disable the hard exit safeguard if you prefer normal interpreter shutdown.
- The tool respects targeting hints (`hints.txt`) to limit patch scope—see `docs/recipes/targeting-hints.md`.
- Texture name mappings (`assets/*/mapping.json`) steer the new texture prefilter and swap pipeline.
- Desktop shell: from the repo root run `npm run tauri:dev` (or `npm run tauri:dev-local` to force a fresh PyInstaller build). The runner automatically ensures `.venv` exists and uses it to execute the CLI in dev/release.
- Husky hooks run `npm run lint` on every commit and `commitlint` on message creation. Use `npm run lint:python`, `npm run lint:rust`, or `npm run lint:frontend` to troubleshoot failures locally.

## Tooling & Hooks

- Run `npm install` at the repo root to install Husky hooks. Pre-commit runs `ruff`, `cargo fmt/clippy`, and `eslint`; `commit-msg` enforces Conventional Commits.
- `npm run lint:python`, `npm run lint:rust`, and `npm run lint:frontend` are available individually when iterating on failures.

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
