# Per-Stylesheet CSS Overrides

This recipe walks through targeting specific Unity `StyleSheet` assets with your CSS variables and selector overrides. Use this when you want file-by-file control instead of applying everything globally across the bundle.

## 1. Folder layout

```
skins/<your_skin>/
├── colours/
│   ├── FMColours.uss
│   ├── AttributeOverrides.css
│   └── mapping.json
├── config.json
└── packages/        # created automatically when you run `patch`
```

The `mapping.json` file can live in either the skin root or the `colours/` folder. The patcher loads both locations and merges the results.

## 2. Author the mapping file

List each CSS file you want to scope as a key. Values are the stylesheet assets to receive those overrides. You can supply a single string, a list of strings, or an object with a `stylesheets` array.

```json
{
  "FMColours.uss": ["FMColours"],
  "AttributeOverrides.css": {
    "stylesheets": ["AttributeColours", "AttributeColoursDark"]
  }
}
```

- **Keys**: accept file names with or without extensions, the bare stem, or a relative path such as `"colours/AttributeOverrides.css"`.
- **Values**: must resolve to stylesheet names exactly as they appear in the bundle (they are case-insensitive at runtime).

Any CSS file *not* listed in `mapping.json` still participates globally. Those overrides apply to every stylesheet unless a more specific mapping exists.

## 3. Write scoped overrides

Inside the mapped CSS files, write the variables and selectors you need.

```css
/* colours/FMColours.uss */
:root {
  --primary: #101e35;
  --secondary: #58b9ff;
}

/* colours/AttributeOverrides.css */
.attribute-colour-great {
  color: #ffc300;
}
```

During patching:

- The variables in `FMColours.uss` only update the `FMColours` stylesheet asset.
- The `.attribute-colour-great` selector override in `AttributeOverrides.css` only touches the `AttributeColours` and `AttributeColoursDark` assets.

## 4. File-stem fallback

When no explicit mapping exists, the patcher still prefers assets whose names match the CSS filename stem. For example, `colours/FMWallpaper.uss` will target an asset named `FMWallpaper` before falling back to global application.

## 5. Run the patch

```bash
python -m fm_skin_builder.cli.main patch skins/<your_skin>
```

- Patched bundles are written back to `skins/<your_skin>/packages` by default.
- Add `--dry-run` to preview changes or `--out build/preview` to redirect the output.
- Use `--debug-export` if you want to inspect the original and patched `.uss` files under the output directory.

## 6. Troubleshooting tips

- Enable `--refresh-scan-cache` if you mapped new assets and the tool still reports "no matching assets". This rebuilds the selector/variable index.
- Keep asset names in the mapping all lower case if you are unsure about casing—the loader normalises everything before comparison.
- Combine mappings with `hints.txt` to narrow patching even further (see `targeting-hints.md`).

With mappings in place you can safely split your overrides into focused files without risking bundle-wide changes.
