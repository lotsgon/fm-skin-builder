# Sprite Extraction Tools

Tools for extracting and browsing sprites from Football Manager sprite atlas bundles.

## Extract Sprites

Extract all sprites from sprite atlas bundles as individual PNG files:

### Extract from a single bundle

```bash
python scripts/extract_sprites.py --bundle bundles/ui-iconspriteatlases_assets_4x.bundle --output extracted_sprites/4x
```

### Extract from all scale bundles

```bash
python scripts/extract_sprites.py --bundle-dir bundles --pattern "ui-iconspriteatlases_assets_*.bundle" --output extracted_sprites/all_scales
```

This will create subdirectories for each scale (1x, 2x, 3x, 4x) containing the extracted sprites.

## Generate Browsable Index

Create an HTML index for easily browsing and searching the extracted sprites:

```bash
python scripts/generate_sprite_index.py --input extracted_sprites/all_scales --output extracted_sprites/sprite_index.html
```

Then open `extracted_sprites/sprite_index.html` in your browser. Features:

- **Search**: Filter sprites by name in real-time
- **Click to copy**: Click any sprite to copy its name to clipboard
- **Organized by scale**: Sprites grouped by 1x, 2x, 3x, 4x
- **Lazy loading**: Efficient handling of thousands of sprites

## Using Extracted Sprites

Once you've extracted sprites, you can:

1. **Browse visually** using the HTML index to find sprites you want to replace
2. **Reference by name** in your `mapping.json`:
   ```json
   {
       "cog_*": "my-custom-settings-icon",
       "star_*": "my-custom-star",
       "kit-squad-outfield": "my-team-kit"
   }
   ```
3. **Name your replacement files** to match the sprite names (without scale suffix):
   - `cog.png` will replace `cog_1x`, `cog_2x`, `cog_3x`, `cog_4x`
   - Or use explicit scale: `cog_4x.png` to only replace the 4x version

## Command Options

### extract_sprites.py

- `--bundle PATH` - Extract from a specific bundle file
- `--bundle-dir PATH` - Directory containing bundles
- `--pattern GLOB` - Glob pattern to match bundles (default: `ui-iconspriteatlases_assets_*.bundle`)
- `--output PATH` - Output directory for extracted PNGs (default: `extracted_sprites`)
- `--verbose` - Enable verbose logging

### generate_sprite_index.py

- `--input PATH` - Directory containing extracted sprites (required)
- `--output PATH` - Output HTML file path (default: `sprite_index.html`)
- `--title TEXT` - Title for the HTML page

## Example Workflow

1. **Extract all sprites**:
   ```bash
   python scripts/extract_sprites.py --bundle-dir bundles --pattern "ui-iconspriteatlases_assets_*.bundle" --output extracted_sprites/icons
   ```

2. **Generate browsable index**:
   ```bash
   python scripts/generate_sprite_index.py --input extracted_sprites/icons --output extracted_sprites/icons/index.html
   ```

3. **Browse and identify sprites**:
   - Open `extracted_sprites/icons/index.html` in your browser
   - Search for sprites (e.g., "cog", "star", "settings")
   - Click sprites to copy their names

4. **Create replacements**:
   - Create your replacement icons in `skins/your_skin/assets/icons/`
   - Name them to match the sprites you want to replace
   - Add mappings in `mapping.json` if needed

5. **Patch bundles**:
   ```bash
   python -m fm_skin_builder.cli.main patch skins/your_skin --out build
   ```

## Notes

- Sprites are extracted from **sprite atlases** (texture sheets that contain multiple sprites)
- Each sprite is saved with its original name from the game
- Scale variants (1x, 2x, 3x, 4x) are organized in separate folders
- The HTML index is self-contained and works offline
- Sprite names may contain special characters that are sanitized for filenames
