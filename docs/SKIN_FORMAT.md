# Skin Config Format (Versioned)

Example (`schema_version` required):
```json
{
  "schema_version": 1,
  "name": "Gold Theme",
  "target_bundle": "fm_base.bundle",
  "output_bundle": "fm_base.bundle",
  "overrides": {
    "ui/skins/base/colours/FMColours.uss": "colours/FMColours.uss"
  },
  "description": "Example theme"
}
```

## Caching
- Cached at `.cache/skins/<skin>/<hash>.json` based on file mtime + content hash.

## Using CSS/USS overrides

- Put overrides in `colours/*.uss` (or `*.css`/`*.uss` at the skin root)
- You can define variables (e.g., `:root { --primary: #112233; }`)
- You can also override selectors, e.g.:

```css
.green { color: #00D3E7; }
```

The patcher applies variable changes and selector overrides across the bundle’s StyleSheets.
If a selector appears in multiple assets, all are updated by default; conflicts are surfaced in logs.

## Patching

- Infer bundle from a skin’s `config.json`:
  - python -m src.cli.main patch skins/your_skin --out build
- Or specify a bundle or directory explicitly:
  - python -m src.cli.main patch skins/your_skin --out build --bundle /path/to/bundles

Options:
- `--dry-run` to preview changes without writing files
- `--patch-direct` to also patch inlined literals
- `--debug-export` to export original/patched `.uss` and JSON for inspection

## Scan (optional)

- Explore variables and selectors with:
  - python -m src.cli.main scan --bundle /path/to/bundle_or_dir --out build/scan --export-uss

This is not required to patch; it’s a reference tool for power users and debugging.
