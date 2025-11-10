#!/usr/bin/env python3
"""Generate an HTML index for browsing extracted sprites.

Creates an HTML file with thumbnails of all extracted sprites, grouped by scale,
making it easy to browse and identify sprites for your icon mappings.

Usage:
    python scripts/generate_sprite_index.py --input extracted_sprites/all_scales --output sprite_index.html
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict
import html


def generate_html_index(sprite_dir: Path, output_file: Path, title: str = "Sprite Index"):
    """Generate an HTML index file for browsing sprites.

    Args:
        sprite_dir: Directory containing extracted sprites (with scale subdirectories)
        output_file: Path to output HTML file
        title: Title for the HTML page
    """
    # Find all PNG files organized by scale
    sprites_by_scale: Dict[str, List[Path]] = {}

    # Check if there are scale subdirectories (1x, 2x, 3x, 4x)
    scale_dirs = [d for d in sprite_dir.iterdir() if d.is_dir() and d.name in [
        '1x', '2x', '3x', '4x']]

    if scale_dirs:
        # Organized by scale
        for scale_dir in sorted(scale_dirs):
            scale = scale_dir.name
            sprites = sorted(scale_dir.glob("*.png"))
            if sprites:
                sprites_by_scale[scale] = sprites
    else:
        # Flat directory
        sprites = sorted(sprite_dir.glob("*.png"))
        if sprites:
            sprites_by_scale["all"] = sprites

    if not sprites_by_scale:
        print(f"No PNG sprites found in {sprite_dir}")
        return

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #fff;
            margin-bottom: 10px;
            font-size: 2em;
        }}
        .info {{
            color: #999;
            margin-bottom: 30px;
            font-size: 0.9em;
        }}
        .search-box {{
            width: 100%;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #2a2a2a;
            color: #fff;
            margin-bottom: 30px;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #4a9eff;
        }}
        .scale-section {{
            margin-bottom: 50px;
        }}
        .scale-header {{
            font-size: 1.5em;
            color: #4a9eff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #333;
        }}
        .sprite-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
        }}
        .sprite-card {{
            background: #2a2a2a;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .sprite-card:hover {{
            border-color: #4a9eff;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(74, 158, 255, 0.2);
        }}
        .sprite-card.hidden {{
            display: none;
        }}
        .sprite-image {{
            width: 100%;
            height: 128px;
            object-fit: contain;
            background: #1a1a1a;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .sprite-name {{
            font-size: 0.85em;
            color: #b0b0b0;
            word-break: break-word;
            font-family: 'Courier New', monospace;
        }}
        .sprite-name mark {{
            background: #4a9eff;
            color: #fff;
            padding: 2px 4px;
            border-radius: 2px;
        }}
        .no-results {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 1.2em;
            display: none;
        }}
        .stats {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{html.escape(title)}</h1>
        <div class="info">
            Browse and search extracted Football Manager sprites. Click on a sprite to copy its name to clipboard.
        </div>

        <input type="text" class="search-box" id="searchBox" placeholder="Search sprites by name (e.g., 'cog', 'star', 'kit')..." autofocus>

        <div class="no-results" id="noResults">No sprites found matching your search.</div>
"""

    # Add each scale section
    for scale, sprites in sprites_by_scale.items():
        sprite_count = len(sprites)
        html_content += f"""
        <div class="scale-section" data-scale="{html.escape(scale)}">
            <h2 class="scale-header">{html.escape(scale.upper())} Scale <span class="stats">({sprite_count} sprites)</span></h2>
            <div class="sprite-grid">
"""

        # Get the relative path from output file to sprite directory
        relative_sprite_dir = sprite_dir.name  # e.g., "all_scales"

        for sprite_path in sprites:
            sprite_name = sprite_path.stem  # Name without .png extension
            safe_name = html.escape(sprite_name)
            # Create relative path from HTML file location to sprite
            img_path = f"{relative_sprite_dir}/{scale}/{sprite_path.name}"

            html_content += f"""
                <div class="sprite-card" data-name="{safe_name.lower()}" onclick="copyToClipboard('{safe_name}')">
                    <img src="{img_path}" alt="{safe_name}" class="sprite-image" loading="lazy">
                    <div class="sprite-name">{safe_name}</div>
                </div>
"""

        html_content += """
            </div>
        </div>
"""

    # Add JavaScript for search and copy
    html_content += """
    </div>

    <script>
        const searchBox = document.getElementById('searchBox');
        const spriteCards = document.querySelectorAll('.sprite-card');
        const noResults = document.getElementById('noResults');
        const scaleSections = document.querySelectorAll('.scale-section');

        // Search functionality
        searchBox.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            let visibleCount = 0;

            spriteCards.forEach(card => {
                const name = card.dataset.name;
                const matches = name.includes(query);
                card.classList.toggle('hidden', !matches);
                if (matches) visibleCount++;
            });

            // Show/hide sections based on whether they have visible cards
            scaleSections.forEach(section => {
                const visibleInSection = section.querySelectorAll('.sprite-card:not(.hidden)').length;
                section.style.display = visibleInSection > 0 ? 'block' : 'none';
            });

            // Show "no results" message
            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        });

        // Copy sprite name to clipboard
        function copyToClipboard(name) {
            navigator.clipboard.writeText(name).then(() => {
                // Visual feedback
                const cards = document.querySelectorAll(`[data-name="${name.toLowerCase()}"]`);
                cards.forEach(card => {
                    const originalBg = card.style.background;
                    card.style.background = '#2a4a2a';
                    setTimeout(() => {
                        card.style.background = originalBg;
                    }, 300);
                });
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        }

        // Keyboard navigation
        searchBox.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchBox.value = '';
                searchBox.dispatchEvent(new Event('input'));
            }
        });
    </script>
</body>
</html>
"""

    # Write HTML file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(html_content, encoding='utf-8')
    print(f"✓ Generated HTML index: {output_file}")
    print(f"  Open in browser: file://{output_file.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML index for browsing extracted sprites"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Directory containing extracted sprites"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("sprite_index.html"),
        help="Output HTML file path (default: sprite_index.html)"
    )
    parser.add_argument(
        "--title",
        default="FM Sprite Index",
        help="Title for the HTML page"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}")
        return 1

    generate_html_index(args.input, args.output, args.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
