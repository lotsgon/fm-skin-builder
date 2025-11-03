# Football Manager 2026 Skin Builder

CSS-first skin patching for Football Manager bundles. Write CSS/USS overrides; we do the rest.

## Try it

- Patch using a skin folder (bundle inferred from config):
	- python -m src.cli.main patch skins/test_skin --out build --dry-run
- Or specify a bundle directory:
	- python -m src.cli.main patch skins/test_skin --out build --bundle bundles --debug-export

Optional flags:
- `--dry-run` preview only
- `--patch-direct` patch inlined literals
- `--debug-export` export original/patched `.uss` + JSON

## Docs

- docs/README.md (overview & quick start)
- docs/recipes/README.md (task-focused guides)
- docs/SKIN_FORMAT.md (skin layout, config, CSS overrides)
- docs/ARCHITECTURE.md (components & data flow)
- docs/ROADMAP.md, docs/TODO.md
