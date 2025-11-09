# Repository Guidelines

## Project Structure & Module Organization
Core code lives under `fm_skin_builder/`, with the CLI exposed via `fm_skin_builder/cli/main.py` (or the `fm-skin` console script). Reusable utilities sit in `fm_skin_builder/core`, while Unity bundle helpers live in `fm_skin_builder/utils`. Sample inputs stay in `skins/` (copy `skins/test_skin` for new work), prebuilt assets in `bundles/`, and build artifacts in `build/`. Tests under `tests/` mirror the module layout so every feature ships with a matching suite. Documentation, recipes, and architectural notes live in `docs/`, and helper shell/python utilities are kept in `scripts/`.

## Build, Test, and Development Commands
`npm install` in the repo root runs the bootstrapper that provisions `.venv/` (Python 3.9.19 via `scripts/setup_python_env.sh` / `.ps1`), installs frontend deps, and wires Husky. Use `python -m fm_skin_builder.cli.main patch skins/your_skin` to apply overrides, and `python -m fm_skin_builder.cli.main scan --bundle bundles --out build/scan --export-uss` to precompute indices. Local smoke tests for a single skin can be done with `python -m fm_skin_builder.cli.main patch skins/test_skin --dry-run`. Run the full suite via `pytest` (or target a file with `pytest tests/test_cli_patch.py -k validation`). Launch the desktop shell from the repo root with `npm run tauri:dev` (one terminal starts Vite + Tauri) or force a fresh backend bundle with `npm run tauri:dev-local`. Format with `black --line-length 100 .` before pushing.

## Coding Style & Naming Conventions
Python uses 4-space indentation, type hints for public interfaces, and descriptive snake_case module/function names. CLI command groups and Click options stay lowercase with hyphenated flag names (e.g., `--dry-run`). Keep configuration JSON files minified, but indent 2 spaces when hand-editing examples. Avoid abbreviations in variable names except for well-known FM terms (`uss`, `css`, `fm`). Prefer dataclasses/Pydantic models for structured data instead of loose dicts.

## Testing Guidelines
Pytest powers all tests; mimic existing names such as `test_cli_patch_sample_skin.py`. Co-locate fixtures in `tests/conftest.py` and add new ones rather than re-creating bundle scaffolding. Any feature touching bundle parsing needs: (1) a CLI test exercising the flag, (2) at least one unit test for the helper module, and (3) texture or vector coverage if assets change. High-level regression tests should run `pytest -m "not slow"` by default; mark long-running bundle scenarios with `@pytest.mark.slow`.

Husky runs `npm run lint` before every commit (`ruff`, `cargo fmt/clippy`, and `eslint`). Make sure the hooks pass locally or run the individual scripts when working outside Git.

## Commit & Pull Request Guidelines
Follow Conventional Commits as seen in the log (`feat:`, `fix:`, `docs:`). Scope names should match modules (`cli`, `patcher`, `textures`) or high-level workflows. PRs need: a problem summary, the command(s) used for verification (`pytest`, `python -m ...`), linked issues, and screenshots/log snippets when touching UI exports. Keep PRs focused; split texture and CSS changes if they can be reviewed independently.

## Asset & Security Notes
Never commit real Football Manager bundles; reference paths like `bundles/sample_x.bundle` instead. `.env` secrets or OS-specific paths belong in your local shell profile, not the repo. Run `python -m fm_skin_builder.cli.main verify --bundle <path>` before sharing third-party skins to ensure no unintended assets leak.
