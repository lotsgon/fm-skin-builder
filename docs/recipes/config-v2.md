# Config v2 quick start

Config v2 keeps things simple: metadata and includes only. No legacy fields.

## Minimal config

Create `skins/<your-skin>/config.json`:

```json
{
  "schema_version": 2,
  "name": "My Skin",
  "author": "You",
  "version": "0.1.0",
  "includes": [
    "assets/icons",
    "assets/backgrounds"
  ],
  "description": "Optional, short summary."
}
```

- `schema_version`: must be 2
- `name`: display name
- `author`, `version`, `description`: optional
- `includes`: opt-in features. Recognized entries so far:
  - `assets/icons` — replace UI icons by Texture2D name
  - `assets/backgrounds` — replace background textures by Texture2D name

## Folder layout

```
skins/
  my_skin/
    config.json
    assets/
      icons/
        Logo.png
      backgrounds/
        PanelBg.png
```

## Run it

Patch against bundles inferred from the repo layout (a `bundles/` folder or a single `*.bundle` at repo root):

```
# Dry-run preview
python -m fm_skin_builder.cli.main patch skins/my_skin --dry-run

# Write outputs next to other build artifacts
python -m fm_skin_builder.cli.main patch skins/my_skin --out build
```

Notes
- CSS/USS patching is still the default-first workflow; includes unlock optional extras like textures.
- Change-aware writes: bundles are only saved if something actually changed.
- Scan cache is used transparently to speed up repeated runs; see the scan recipe for more details.
