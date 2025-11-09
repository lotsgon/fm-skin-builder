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

### Targeting specific StyleSheets

- Create a `mapping.json` next to your CSS files (skin root or `colours/`).
- Each key can be a file name, stem, or relative path. Values can be a single stylesheet name or a list under `"stylesheets"`.

```json
{
  "FMColours.uss": ["FMColours"],
  "colours/AttributeOverrides.css": {
    "stylesheets": ["AttributeColours", "AttributeColoursDark"]
  }
}
```

- Mapped files only apply to the listed stylesheet assets. Files without a mapping still apply globally, but the pipeline tries to match assets whose names share the CSS filename stem first.

The patcher merges global variables/selectors and per-asset overrides before patching, preserving the previous behaviour while enabling precise scoping when needed.

## Patching

- Infer bundle from a skin’s `config.json`:
  - python -m fm_skin_builder.cli.main patch skins/your_skin
- Or specify a bundle or directory explicitly:
  - python -m fm_skin_builder.cli.main patch skins/your_skin --bundle /path/to/bundles

- Options:
  - `--out <dir>` to override the default `<skin>/packages` output directory
  - `--dry-run` to preview changes without writing files
  - `--patch-direct` to also patch inlined literals
  - `--debug-export` to export original/patched `.uss` and JSON for inspection

## Scan (optional)

- Explore variables and selectors with:
  - python -m fm_skin_builder.cli.main scan --bundle /path/to/bundle_or_dir --out build/scan --export-uss

This is not required to patch; it’s a reference tool for power users and debugging.
