# Test Skin (Sample)

This is a minimal skin used by tests and as a quick-start example.

- config.json points to a bundle name `fm_base.bundle` (tests override this to a temp file path).
- colours/base.uss defines:
  - CSS variables: `--primary`, `--accent`
  - A class selector `.green` with a literal color

Use via CLI (example):

- Infer bundle from config.json:
  - python -m src.cli.main patch skins/test_skin --out build --dry-run
- Explicit bundle directory:
  - python -m src.cli.main patch skins/test_skin --out build --bundle /path/to/bundles --patch-direct

Notes:
- Use `--dry-run` to preview changes without writing files.
- Add `--debug-export` to export original/patched `.uss` + JSON when actually writing bundles.

