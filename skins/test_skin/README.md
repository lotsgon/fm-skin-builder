# Test Skin (Sample)

This is a minimal skin used by tests and as a quick-start example.

- config.json points to a bundle name `fm_base.bundle` (tests override this to a temp file path).
- colours/base.uss defines:
  - CSS variables: `--primary`, `--accent`
  - A class selector `.green` with a literal color

Use via CLI (example):

- Infer bundle from config.json:
  - python -m src.cli.main patch skins/test_skin --out build --debug-export
- Explicit bundle directory:
  - python -m src.cli.main patch skins/test_skin --out build --bundle /path/to/bundles --patch-direct

Note: The repository does not include any real FM bundles. Tests mock UnityPy and create temporary fake bundles.
