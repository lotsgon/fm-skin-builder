# Debug exports

Add --debug-export to write .uss and JSON snapshots for original and patched StyleSheets next to your output folder.

- python -m src.cli.main patch skins/your_skin --out build --debug-export

What you’ll see

- build/debug_uss/original_<name>.uss and patched_<name>.uss
- build/debug_uss/original_<name>.json and patched_<name>.json
- Minimal JSON variants with strings/colors arrays for faster diffing

Notes

- Debug exports are only written when changes occur (and not in --dry-run).
- Use with version control or diff tools to inspect changes safely.
