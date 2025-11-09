# Replace background images (Texture2D)

Replace background textures that appear in panels or screens.

## 1) Opt in via includes

`skins/<skin>/config.json`:

```json
{
  "schema_version": 2,
  "name": "Demo",
  "includes": ["assets/backgrounds"]
}
```

## 2) Place images

- Put files in `skins/<skin>/assets/backgrounds/`
- File name (without extension) must match the Texture2D name in the bundle.
- Supported extensions: `.png`, `.jpg`, `.jpeg`

Examples:
```
assets/backgrounds/
  PanelBg.png
  PanelBg_x2.png
  PanelBg_x4.png
```

You can also use `Name@2x.png`, `Name@4x.png` suffixes. Cross-format replacements (e.g., replacing a PNG-named texture with a JPG file) are allowed; a warning is logged and the replacement still applies.

## 3) Run the patcher

```
python -m fm_skin_builder.cli.main patch skins/<skin> --out build
```

- Add `--dry-run` to preview.

## Optional: name mapping (mapping.json)

If your file names don't match the bundle's Texture2D or container/sprite names, add a mapping file:

- Global (applies to both icons and backgrounds): `skins/<skin>/assets/mapping.json` (or `map.json`)
- Type-specific (overrides global): `skins/<skin>/assets/backgrounds/mapping.json` (or `map.json`)

Mapping (unique keys): target → source

```json
{
  "Sky Bet League One": "my_background",
  "premier_league_skin_fm26_x2": "alt"
}
```

- Keys are the target asset/alias names in the bundle (can include spaces), optionally with variant suffix.
- Values are your replacement filename stems (extension ignored).
- If the key includes a variant (like `_x2`), we look for that same variant on the source; otherwise we map all available variants from the source.
- Only contents are replaced; Unity asset names are not renamed.

Legacy source → target mapping is no longer supported to prevent ambiguity when multiple targets share one source or when file stems clash with existing asset names. Please migrate skins to the target → source form.

## Format and size warnings

- If the replacement format differs from the bundle (e.g., bundle is PNG but you provide JPG), a warning is logged and the replacement still proceeds.
- If the replacement image dimensions differ from the target Texture2D’s width/height, a warning is logged and the replacement still proceeds (no automatic scaling is performed).

## Variant awareness and warnings

- If multiple variants exist in the bundle (1x/2x/4x) but you provide only a subset, the patcher logs a warning and replaces only the provided variants.
- No auto-scaling is performed.

## Troubleshooting

- Use `--debug-export` to export assets and discover the exact Texture2D names.
- If nothing gets written, confirm that the names match and that your config includes the correct feature.
