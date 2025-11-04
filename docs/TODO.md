# Development TODO (current)

This checklist reflects the active state on branch `feat/texture-replacement` as of 2025-11-03.

- [x] CSS-first patching (variables + selector overrides), dry-run, change-aware saves
- [x] Scan/index with transparent cache and optional `.uss` debug exports
- [x] Conflict surfacing in logs; optional targeting hints
- [x] Config v2 (metadata + includes) and bundle inference
- [x] Texture swapping (icons/backgrounds):
  - [x] Variant-aware (`_x2` / `@2x`, `_x4` / `@4x`) with warnings when partial
  - [x] Extension-agnostic matches + cross-format warnings
  - [x] Alias matching via AssetBundle `m_Container` and Sprite -> Texture2D
  - [x] Optional size warnings (compare replacement vs Texture2D width/height)
  - [x] Optional name mapping: `assets/mapping.json` and `assets/{icons,backgrounds}/mapping.json`

Next up

- [ ] Icons coverage: mapping.json + alias + variant tests mirroring backgrounds
- [ ] Optional `--debug-textures` to print a richer list of candidate names/variants
- [ ] Optional `--strict-texture-size` (fail on mismatch instead of warn)
- [ ] README/docs: link mapping docs from main README and recipes index

Future work

- [ ] Font replacement MVP (in-place)
- [ ] Data assets patching (+CustomData)
- [ ] Safe var/class augmentation phases
- [ ] Auto-discovery of common installation paths (bundle root)

Known Limitations

- [ ] **Vector sprite modification** - While we can successfully modify vector sprite mesh data (vertices, indices, colors) in Sprite objects, these changes don't appear visually in-game. The modified sprites reference a SpriteAtlas (external bundle) which seems to take precedence during rendering. Possible solutions to investigate:
  - Modify the actual SpriteAtlas texture that kit sprites reference
  - Find the correct render flags/settings to force mesh rendering over texture
  - Investigate if kit sprites use a special shader that ignores vertex data
  - Example affected sprites: `kit-squad-outfield`, `kit-squad-goalkeeper` in `ui-icons_assets_*.bundle`
