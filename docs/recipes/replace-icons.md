# Replace app icons (Texture2D)

This shows how to replace icon textures by name with optional high-DPI variants.

## 1) Opt in via includes

`skins/<skin>/config.json`:

```json
{
  "schema_version": 2,
  "name": "Demo",
  "includes": ["assets/icons"]
}
```

## 2) Place images

- Put files in `skins/<skin>/assets/icons/`
- File name (without extension) must match the Texture2D name in the bundle.
- Supported extensions: `.png`, `.jpg`, `.jpeg`

Examples:
```
assets/icons/
  Search.png          # 1x
  Search_x2.png       # 2x (retina)
  Search_x4.png       # 4x (ultra-high DPI)
```

Also supported: `Name@2x.png`, `Name@4x.png`. Cross-format replacements (e.g., bundle texture named with PNG but you provide JPG) are allowed; the tool logs a warning and proceeds.

## 3) Run the patcher

```
python -m fm_skin_builder.cli.main patch skins/<skin> --out build
```

- Use `--dry-run` to preview without writing files.

## Optional: name mapping (mapping.json)

If your file names don't match the bundle's Texture2D or container/sprite names, add a mapping file:

- Global (applies to both icons and backgrounds): `skins/<skin>/assets/mapping.json` (or `map.json`)
- Type-specific (overrides global): `skins/<skin>/assets/icons/mapping.json` (or `map.json`)

Mapping (unique keys): target → source

```json
{
  "Search": "my_icon",
  "AppLogo_x2": "logo"
}
```

- Keys are the target asset/alias names in the bundle (unique), optionally with variant suffix (e.g., `AppLogo_x2`).
- Values are your replacement filename stems (extension ignored), e.g., `my_icon.png`.
- If the key includes a variant (like `_x2` or `@2x`), we look for that same variant on the source; otherwise we map all available variants from the source.
- Only contents are replaced; Unity asset names are not renamed.

Legacy source → target mapping is no longer supported to prevent ambiguity when multiple targets share one source or when file stems clash with existing asset names. Please migrate skins to the target → source form.

## Format and size warnings

- If the replacement format differs from the bundle (e.g., PNG vs JPG), a warning is logged and the replacement still proceeds.
- If the replacement image dimensions differ from the target Texture2D’s width/height, a warning is logged and the replacement still proceeds (no automatic scaling is performed).

## Variant awareness and warnings

- If the bundle contains variants for a texture (e.g., `Search`, `Search_x2`, `Search_x4`) and you only provide one of them, you'll get a warning like:
  `Only 1/3 variants provided for 'Search' (provided: [1], missing: [2, 4])`
- The patcher replaces only the provided matching variants and skips missing ones.
- It does not upscale/downscale automatically — provide the proper sizes for the best results.

## Tips

- Start with 1x first to validate name matching.
- Add 2x and 4x variants as needed for crisp rendering on high-DPI displays.
- Use `--debug-export` to export and inspect bundle contents if you're unsure about the texture names.

## Troubleshooting

- No matches for an icon bundle (e.g., ui-icons_assets_4x.bundle): Many icon bundles contain Sprites that reference Texture2D data stored in another bundle (often a *_assets_common.bundle). If you see the hint about sprites referencing textures in another bundle, run the patcher against the common bundle as well (or the entire bundles/ directory). Use the scan cache output in `.cache/skins/<skin>/<bundle>.index.json` to inspect `textures`, `sprites`, and `aliases` lists.
- Atlas textures: If a Texture2D is shared by multiple Sprites (atlas-like), replacements are blocked for safety and logged as an error.
