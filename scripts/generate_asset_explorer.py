#!/usr/bin/env python3
"""Generate interactive HTML explorer from FM asset catalog.

Creates a searchable, browsable interface for exploring all FM assets including:
- CSS variables and classes
- UXML files
- Backgrounds and textures
- Sprites and icons
- Fonts

Usage:
    python scripts/generate_asset_explorer.py --input extracted_sprites/css_uxml_catalog.json --output extracted_sprites/asset_explorer.html
"""

import argparse
import sys
import json
import html
from pathlib import Path


def generate_explorer_html(catalog_path: Path, output_path: Path, title: str = "FM Asset Explorer") -> None:
    """Generate HTML explorer from catalog JSON."""

    # Load catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    css_vars = catalog.get("css_variables", {})
    css_classes = catalog.get("css_classes", {})
    uxml_files = catalog.get("uxml_files", {})
    stylesheets = catalog.get("stylesheets", {})
    backgrounds = catalog.get("backgrounds", {})
    textures = catalog.get("textures", {})
    sprites = catalog.get("sprites", {})
    fonts = catalog.get("fonts", {})
    videos = catalog.get("videos", {})

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 20px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        h1 {{
            color: #58a6ff;
            margin-bottom: 10px;
            font-size: 2.5em;
            font-weight: 600;
        }}
        .subtitle {{
            color: #8b949e;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        .search-container {{
            position: sticky;
            top: 0;
            background: #0d1117;
            padding: 20px 0;
            z-index: 100;
            border-bottom: 1px solid #21262d;
            margin-bottom: 30px;
        }}
        .search-box {{
            width: 100%;
            padding: 15px 20px;
            font-size: 16px;
            border: 1px solid #30363d;
            border-radius: 6px;
            background: #161b22;
            color: #c9d1d9;
            transition: all 0.2s;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #58a6ff;
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.3);
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        .tab {{
            padding: 10px 20px;
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 500;
        }}
        .tab:hover {{
            border-color: #58a6ff;
            background: #1c2128;
        }}
        .tab.active {{
            background: #388bfd;
            border-color: #388bfd;
            color: #ffffff;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .asset-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .asset-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 20px;
            transition: all 0.2s;
        }}
        .asset-card:hover {{
            border-color: #58a6ff;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }}
        .asset-card.hidden {{
            display: none;
        }}
        .asset-name {{
            font-size: 1.1em;
            color: #58a6ff;
            margin-bottom: 10px;
            font-family: 'SF Mono', 'Monaco', 'Cascadia Code', monospace;
            cursor: pointer;
            word-break: break-word;
        }}
        .asset-name:hover {{
            text-decoration: underline;
        }}
        .asset-meta {{
            color: #8b949e;
            font-size: 0.9em;
            margin-bottom: 12px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .meta-badge {{
            background: #21262d;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        .asset-refs {{
            margin-top: 12px;
        }}
        .ref-section {{
            margin-bottom: 10px;
        }}
        .ref-label {{
            color: #58a6ff;
            font-weight: 600;
            margin-right: 8px;
            font-size: 0.9em;
        }}
        .ref-item {{
            display: inline-block;
            background: #21262d;
            padding: 4px 10px;
            margin: 3px;
            border-radius: 4px;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .ref-item:hover {{
            background: #30363d;
        }}
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #8b949e;
            font-size: 1.3em;
            display: none;
        }}
        .stats {{
            background: #161b22;
            padding: 25px;
            border-radius: 6px;
            margin-bottom: 30px;
            border: 1px solid #30363d;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            color: #58a6ff;
            font-weight: 700;
        }}
        .stat-label {{
            color: #8b949e;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .toast {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #238636;
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s;
            pointer-events: none;
        }}
        .toast.show {{
            opacity: 1;
            transform: translateY(0);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{html.escape(title)}</h1>
        <div class="subtitle">
            Browse and search all FM assets and their relationships. Click names to copy to clipboard.
        </div>

        <div class="stats">
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value">{len(css_vars)}</div>
                    <div class="stat-label">CSS Variables</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(css_classes)}</div>
                    <div class="stat-label">CSS Classes</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(uxml_files)}</div>
                    <div class="stat-label">UXML Files</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(backgrounds)}</div>
                    <div class="stat-label">Backgrounds</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(textures)}</div>
                    <div class="stat-label">Textures</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(sprites)}</div>
                    <div class="stat-label">Sprites</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(fonts)}</div>
                    <div class="stat-label">Fonts</div>
                </div>
            </div>
        </div>

        <div class="search-container">
            <input type="text" class="search-box" id="searchBox" placeholder="Search assets (e.g., '--primary', '.button', 'Background', 'icon')..." autofocus>
            <div class="tabs">
                <div class="tab active" data-tab="all">All Assets</div>
                <div class="tab" data-tab="vars">CSS Variables <span style="opacity:0.6">({len(css_vars)})</span></div>
                <div class="tab" data-tab="classes">CSS Classes <span style="opacity:0.6">({len(css_classes)})</span></div>
                <div class="tab" data-tab="uxml">UXML Files <span style="opacity:0.6">({len(uxml_files)})</span></div>
                <div class="tab" data-tab="backgrounds">Backgrounds <span style="opacity:0.6">({len(backgrounds)})</span></div>
                <div class="tab" data-tab="textures">Textures <span style="opacity:0.6">({len(textures)})</span></div>
                <div class="tab" data-tab="sprites">Sprites <span style="opacity:0.6">({len(sprites)})</span></div>
                <div class="tab" data-tab="fonts">Fonts <span style="opacity:0.6">({len(fonts)})</span></div>
            </div>
        </div>

        <div class="no-results" id="noResults">No assets found matching your search.</div>

        <div class="tab-content active" data-tab="all">
            <div class="asset-grid" id="allAssets"></div>
        </div>
        <div class="tab-content" data-tab="vars">
            <div class="asset-grid" id="varAssets"></div>
        </div>
        <div class="tab-content" data-tab="classes">
            <div class="asset-grid" id="classAssets"></div>
        </div>
        <div class="tab-content" data-tab="uxml">
            <div class="asset-grid" id="uxmlAssets"></div>
        </div>
        <div class="tab-content" data-tab="backgrounds">
            <div class="asset-grid" id="bgAssets"></div>
        </div>
        <div class="tab-content" data-tab="textures">
            <div class="asset-grid" id="texAssets"></div>
        </div>
        <div class="tab-content" data-tab="sprites">
            <div class="asset-grid" id="spriteAssets"></div>
        </div>
        <div class="tab-content" data-tab="fonts">
            <div class="asset-grid" id="fontAssets"></div>
        </div>
    </div>

    <div class="toast" id="toast">Copied to clipboard!</div>

    <script>
        const catalog = {json.dumps(catalog, ensure_ascii=False)};

        // Render functions
        function renderCard(name, info, type) {{
            const card = document.createElement('div');
            card.className = 'asset-card';
            card.dataset.name = name.toLowerCase();
            card.dataset.type = type;

            let html = `<div class="asset-name" onclick="copyToClipboard('${{name}}')">${{name}}</div>`;
            html += `<div class="asset-meta">`;

            if (type === 'var') {{
                html += `<span class="meta-badge">CSS Variable</span>`;
                if (info.defined_in && info.defined_in.length > 0) {{
                    html += `<span class="meta-badge">${{info.defined_in.length}} definitions</span>`;
                }}
            }} else if (type === 'class') {{
                html += `<span class="meta-badge">CSS Class</span>`;
                const propCount = Object.keys(info.properties || {{}}).length;
                if (propCount > 0) {{
                    html += `<span class="meta-badge">${{propCount}} properties</span>`;
                }}
            }} else if (type === 'uxml') {{
                html += `<span class="meta-badge">UXML</span>`;
                if (info.bundle) {{
                    html += `<span class="meta-badge">${{info.bundle}}</span>`;
                }}
            }} else if (type === 'background' || type === 'texture') {{
                html += `<span class="meta-badge">${{type === 'background' ? 'Background' : 'Texture'}}</span>`;
                if (info.dimensions) {{
                    html += `<span class="meta-badge">${{info.dimensions.width}}×${{info.dimensions.height}}</span>`;
                }}
            }} else if (type === 'sprite') {{
                html += `<span class="meta-badge">Sprite</span>`;
                if (info.dimensions) {{
                    html += `<span class="meta-badge">${{info.dimensions.width}}×${{info.dimensions.height}}</span>`;
                }}
            }} else if (type === 'font') {{
                html += `<span class="meta-badge">Font</span>`;
            }}

            html += `</div>`;

            // References
            html += `<div class="asset-refs">`;

            if (type === 'var' && info.used_in_uxml && info.used_in_uxml.length > 0) {{
                html += `<div class="ref-section"><span class="ref-label">Used in:</span>`;
                info.used_in_uxml.slice(0, 5).forEach(ref => {{
                    html += `<span class="ref-item">${{ref}}</span>`;
                }});
                if (info.used_in_uxml.length > 5) {{
                    html += `<span class="ref-item">+${{info.used_in_uxml.length - 5}} more</span>`;
                }}
                html += `</div>`;
            }}

            if (type === 'class' && info.used_in_uxml && info.used_in_uxml.length > 0) {{
                html += `<div class="ref-section"><span class="ref-label">Used in:</span>`;
                info.used_in_uxml.slice(0, 5).forEach(ref => {{
                    html += `<span class="ref-item">${{ref}}</span>`;
                }});
                if (info.used_in_uxml.length > 5) {{
                    html += `<span class="ref-item">+${{info.used_in_uxml.length - 5}} more</span>`;
                }}
                html += `</div>`;
            }}

            html += `</div>`;

            card.innerHTML = html;
            return card;
        }}

        // Populate grids
        const allGrid = document.getElementById('allAssets');
        const varGrid = document.getElementById('varAssets');
        const classGrid = document.getElementById('classAssets');
        const uxmlGrid = document.getElementById('uxmlAssets');
        const bgGrid = document.getElementById('bgAssets');
        const texGrid = document.getElementById('texAssets');
        const spriteGrid = document.getElementById('spriteAssets');
        const fontGrid = document.getElementById('fontAssets');

        // Render all assets
        Object.entries(catalog.css_variables || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'var');
            allGrid.appendChild(card.cloneNode(true));
            varGrid.appendChild(card);
        }});

        Object.entries(catalog.css_classes || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'class');
            allGrid.appendChild(card.cloneNode(true));
            classGrid.appendChild(card);
        }});

        Object.entries(catalog.uxml_files || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'uxml');
            allGrid.appendChild(card.cloneNode(true));
            uxmlGrid.appendChild(card);
        }});

        Object.entries(catalog.backgrounds || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'background');
            allGrid.appendChild(card.cloneNode(true));
            bgGrid.appendChild(card);
        }});

        Object.entries(catalog.textures || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'texture');
            allGrid.appendChild(card.cloneNode(true));
            texGrid.appendChild(card);
        }});

        Object.entries(catalog.sprites || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'sprite');
            allGrid.appendChild(card.cloneNode(true));
            spriteGrid.appendChild(card);
        }});

        Object.entries(catalog.fonts || {{}}).forEach(([name, info]) => {{
            const card = renderCard(name, info, 'font');
            allGrid.appendChild(card.cloneNode(true));
            fontGrid.appendChild(card);
        }});

        // Tab switching
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');
        let currentTab = 'all';

        tabs.forEach(tab => {{
            tab.addEventListener('click', () => {{
                const tabName = tab.dataset.tab;
                currentTab = tabName;

                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                tabContents.forEach(content => {{
                    content.classList.remove('active');
                    if (content.dataset.tab === tabName) {{
                        content.classList.add('active');
                    }}
                }});

                // Trigger search update
                document.getElementById('searchBox').dispatchEvent(new Event('input'));
            }});
        }});

        // Search
        const searchBox = document.getElementById('searchBox');
        const noResults = document.getElementById('noResults');

        searchBox.addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();
            const activeGrid = document.querySelector(`.tab-content.active .asset-grid`);
            const cards = activeGrid.querySelectorAll('.asset-card');
            let visibleCount = 0;

            cards.forEach(card => {{
                const name = card.dataset.name;
                if (!query || name.includes(query)) {{
                    card.classList.remove('hidden');
                    visibleCount++;
                }} else {{
                    card.classList.add('hidden');
                }}
            }});

            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }});

        // Copy to clipboard
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => {{
                    toast.classList.remove('show');
                }}, 2000);
            }});
        }}
    </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding='utf-8')

    print(f"✓ Generated asset explorer: {output_path}")
    print(f"  Total assets: {len(css_vars) + len(css_classes) + len(uxml_files) + len(backgrounds) + len(textures) + len(sprites) + len(fonts) + len(videos)}")
    print(f"  Open in browser: file://{output_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML explorer from asset catalog"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="Input catalog JSON file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("asset_explorer.html"),
        help="Output HTML file (default: asset_explorer.html)"
    )
    parser.add_argument(
        "--title",
        default="FM Asset Explorer",
        help="Page title"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Catalog not found: {args.input}")
        return 1

    generate_explorer_html(args.input, args.output, args.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
