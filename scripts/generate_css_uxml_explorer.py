#!/usr/bin/env python3
"""Generate an interactive HTML explorer for CSS ↔ UXML catalog.

Creates a searchable HTML interface for browsing CSS variables, classes,
UXML files, and their cross-references.

Usage:
    python scripts/generate_css_uxml_explorer.py --input extracted_sprites/css_uxml_catalog.json --output extracted_sprites/css_uxml_explorer.html
"""

import argparse
import json
import sys
from pathlib import Path
import html


def generate_html_explorer(catalog_path: Path, output_path: Path, title: str = "CSS & UXML Explorer"):
    """Generate an interactive HTML explorer from the catalog."""

    # Load catalog
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    css_variables = catalog.get("css_variables", {})
    css_classes = catalog.get("css_classes", {})
    uxml_files = catalog.get("uxml_files", {})
    stylesheets = catalog.get("stylesheets", {})

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
        .controls {{
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .search-box {{
            flex: 1;
            min-width: 300px;
            padding: 12px 20px;
            font-size: 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #2a2a2a;
            color: #fff;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #4a9eff;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
        }}
        .tab {{
            padding: 12px 24px;
            background: #2a2a2a;
            border: none;
            color: #999;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            border-radius: 8px 8px 0 0;
            transition: all 0.2s;
        }}
        .tab:hover {{
            color: #fff;
            background: #333;
        }}
        .tab.active {{
            color: #fff;
            background: #4a9eff;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .stats {{
            display: flex;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        .stat {{
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #333;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4a9eff;
        }}
        .stat-label {{
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .item-grid {{
            display: grid;
            gap: 15px;
        }}
        .item-card {{
            background: #2a2a2a;
            border: 2px solid #333;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s;
        }}
        .item-card:hover {{
            border-color: #4a9eff;
            box-shadow: 0 4px 12px rgba(74, 158, 255, 0.2);
        }}
        .item-card.hidden {{
            display: none;
        }}
        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        .item-name {{
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            color: #4a9eff;
            font-weight: bold;
            word-break: break-word;
        }}
        .item-badge {{
            background: #333;
            color: #999;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            white-space: nowrap;
        }}
        .item-details {{
            display: grid;
            gap: 10px;
        }}
        .detail-row {{
            display: flex;
            gap: 10px;
            font-size: 0.9em;
        }}
        .detail-label {{
            color: #999;
            min-width: 120px;
        }}
        .detail-value {{
            color: #e0e0e0;
            flex: 1;
        }}
        .tag-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .tag {{
            background: #333;
            color: #b0b0b0;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-family: 'Courier New', monospace;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tag:hover {{
            background: #4a9eff;
            color: #fff;
        }}
        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
            font-size: 1.2em;
        }}
        .expandable {{
            margin-top: 10px;
            border-top: 1px solid #333;
            padding-top: 10px;
        }}
        .expand-btn {{
            background: #333;
            border: none;
            color: #4a9eff;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            margin-top: 5px;
            transition: all 0.2s;
        }}
        .expand-btn:hover {{
            background: #4a9eff;
            color: #fff;
        }}
        .expanded-content {{
            margin-top: 10px;
            padding: 10px;
            background: #1a1a1a;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            display: none;
        }}
        .expanded-content.show {{
            display: block;
        }}
        .copy-btn {{
            background: none;
            border: none;
            color: #4a9eff;
            cursor: pointer;
            padding: 4px;
            margin-left: 8px;
            font-size: 0.9em;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{
            color: #fff;
        }}
        .preview-btn {{
            background: #333;
            border: none;
            color: #4a9eff;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            margin-top: 10px;
            transition: all 0.2s;
        }}
        .preview-btn:hover {{
            background: #4a9eff;
            color: #fff;
        }}
        .preview-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            overflow: auto;
        }}
        .preview-overlay.show {{
            display: block;
        }}
        .preview-content {{
            max-width: 1200px;
            margin: 40px auto;
            background: #1a1a1a;
            border-radius: 8px;
            border: 2px solid #333;
            position: relative;
        }}
        .preview-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 2px solid #333;
        }}
        .preview-title {{
            font-size: 1.2em;
            color: #4a9eff;
            font-family: 'Courier New', monospace;
        }}
        .preview-close {{
            background: none;
            border: none;
            color: #999;
            font-size: 1.5em;
            cursor: pointer;
            padding: 5px 10px;
            transition: all 0.2s;
        }}
        .preview-close:hover {{
            color: #fff;
        }}
        .preview-body {{
            padding: 20px;
            max-height: 70vh;
            overflow: auto;
        }}
        .preview-code {{
            background: #0d0d0d;
            padding: 20px;
            border-radius: 4px;
            font-family: 'Courier New', Consolas, monospace;
            font-size: 0.9em;
            line-height: 1.6;
            color: #e0e0e0;
            white-space: pre;
            overflow-x: auto;
        }}
        .preview-code .css-selector {{
            color: #4a9eff;
        }}
        .preview-code .css-property {{
            color: #c792ea;
        }}
        .preview-code .css-value {{
            color: #c3e88d;
        }}
        .preview-code .xml-tag {{
            color: #89ddff;
        }}
        .preview-code .xml-attribute {{
            color: #c792ea;
        }}
        .preview-code .xml-string {{
            color: #c3e88d;
        }}
        .preview-loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        .preview-error {{
            color: #ff5555;
            padding: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{html.escape(title)}</h1>
        <div class="info">
            Search and explore CSS variables, classes, UXML files, and their relationships in Football Manager.
        </div>

        <div class="controls">
            <input type="text" class="search-box" id="searchBox" placeholder="Search by name (e.g., '--primary', '.green', 'MainMenu')..." autofocus>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(css_variables)}</div>
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
                <div class="stat-value">{len(stylesheets)}</div>
                <div class="stat-label">Stylesheets</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="variables">CSS Variables</button>
            <button class="tab" data-tab="classes">CSS Classes</button>
            <button class="tab" data-tab="uxml">UXML Files</button>
            <button class="tab" data-tab="stylesheets">Stylesheets</button>
        </div>

        <!-- CSS Variables Tab -->
        <div id="variables" class="tab-content active">
            <div class="item-grid" id="variables-grid">
"""

    # Generate CSS Variables
    for var_name, var_data in sorted(css_variables.items()):
        defined_in = var_data.get("defined_in", [])
        used_in_stylesheets = var_data.get("used_in_stylesheets", [])
        used_in_uxml = var_data.get("used_in_uxml", [])
        total_usage = len(used_in_stylesheets) + len(used_in_uxml)

        html_content += f"""
                <div class="item-card" data-name="{html.escape(var_name.lower())}" data-type="variable">
                    <div class="item-header">
                        <div class="item-name">{html.escape(var_name)}
                            <button class="copy-btn" onclick="copyToClipboard('{html.escape(var_name, quote=True)}')">📋</button>
                        </div>
                        <div class="item-badge">{total_usage} usage(s)</div>
                    </div>
                    <div class="item-details">
                        <div class="detail-row">
                            <div class="detail-label">Defined in:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
        for sheet in defined_in:
            html_content += f'                                    <div class="tag">{html.escape(sheet)}</div>\n'

        html_content += """                                </div>
                            </div>
                        </div>
"""

        if used_in_stylesheets:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Used in CSS:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for sheet in used_in_stylesheets[:10]:  # Limit to 10
                html_content += f'                                    <div class="tag">{html.escape(sheet)}</div>\n'
            if len(used_in_stylesheets) > 10:
                html_content += f'                                    <div class="tag">+{len(used_in_stylesheets) - 10} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if used_in_uxml:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Used in UXML:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for uxml in used_in_uxml[:10]:
                html_content += f'                                    <div class="tag">{html.escape(uxml)}</div>\n'
            if len(used_in_uxml) > 10:
                html_content += f'                                    <div class="tag">+{len(used_in_uxml) - 10} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        html_content += """                    </div>
                </div>
"""

    html_content += """            </div>
        </div>

        <!-- CSS Classes Tab -->
        <div id="classes" class="tab-content">
            <div class="item-grid" id="classes-grid">
"""

    # Generate CSS Classes
    for class_name, class_data in sorted(css_classes.items()):
        defined_in = class_data.get("defined_in", [])
        used_in_uxml = class_data.get("used_in_uxml", [])
        properties = class_data.get("properties", {})

        html_content += f"""
                <div class="item-card" data-name="{html.escape(class_name.lower())}" data-type="class">
                    <div class="item-header">
                        <div class="item-name">{html.escape(class_name)}
                            <button class="copy-btn" onclick="copyToClipboard('{html.escape(class_name, quote=True)}')">📋</button>
                        </div>
                        <div class="item-badge">{len(used_in_uxml)} usage(s)</div>
                    </div>
                    <div class="item-details">
                        <div class="detail-row">
                            <div class="detail-label">Defined in:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
        for sheet in defined_in:
            html_content += f'                                    <div class="tag">{html.escape(sheet)}</div>\n'

        html_content += """                                </div>
                            </div>
                        </div>
"""

        if used_in_uxml:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Used in UXML:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for uxml in used_in_uxml[:10]:
                html_content += f'                                    <div class="tag">{html.escape(uxml)}</div>\n'
            if len(used_in_uxml) > 10:
                html_content += f'                                    <div class="tag">+{len(used_in_uxml) - 10} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if properties:
            prop_count = len(properties)
            html_content += f"""
                        <div class="expandable">
                            <button class="expand-btn" onclick="toggleExpand(this)">Show {prop_count} properties</button>
                            <div class="expanded-content">
"""
            for prop_name, prop_values in list(properties.items())[:20]:  # Limit to 20
                values_str = ", ".join([str(v.get("value", ""))
                                       for v in prop_values[:3]])
                html_content += f'                                <div>{html.escape(prop_name)}: {html.escape(values_str)}</div>\n'
            html_content += """                            </div>
                        </div>
"""

        html_content += """                    </div>
                </div>
"""

    html_content += """            </div>
        </div>

        <!-- UXML Files Tab -->
        <div id="uxml" class="tab-content">
            <div class="item-grid" id="uxml-grid">
"""

    # Generate UXML Files
    for uxml_name, uxml_data in sorted(uxml_files.items()):
        bundle = uxml_data.get("bundle", "")
        stylesheets_used = uxml_data.get("stylesheets", [])
        has_inline = uxml_data.get("has_inline_styles", False)
        classes_used = uxml_data.get("classes_used", [])
        variables_used = uxml_data.get("variables_used", [])
        elements = uxml_data.get("elements", [])
        export_path = uxml_data.get("export_path", "")

        html_content += f"""
                <div class="item-card" data-name="{html.escape(uxml_name.lower())}" data-type="uxml" data-export="{html.escape(export_path)}">
                    <div class="item-header">
                        <div class="item-name">{html.escape(uxml_name)}
                            <button class="copy-btn" onclick="copyToClipboard('{html.escape(uxml_name, quote=True)}')">📋</button>
                        </div>
                        <div class="item-badge">{html.escape(bundle)}</div>
                    </div>
                    <div class="item-details">
"""

        if stylesheets_used:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Stylesheets:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for sheet in stylesheets_used:
                html_content += f'                                    <div class="tag">{html.escape(sheet)}</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if has_inline:
            html_content += """
                        <div class="detail-row">
                            <div class="detail-label">Inline Styles:</div>
                            <div class="detail-value">✓ Yes</div>
                        </div>
"""

        if classes_used:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Classes Used:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for cls in classes_used[:15]:
                html_content += f'                                    <div class="tag">{html.escape(cls)}</div>\n'
            if len(classes_used) > 15:
                html_content += f'                                    <div class="tag">+{len(classes_used) - 15} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if variables_used:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Variables Used:</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for var in variables_used[:10]:
                html_content += f'                                    <div class="tag">{html.escape(var)}</div>\n'
            if len(variables_used) > 10:
                html_content += f'                                    <div class="tag">+{len(variables_used) - 10} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if elements:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Elements:</div>
                            <div class="detail-value">{html.escape(", ".join(elements[:10]))}</div>
                        </div>
"""

        if export_path:
            html_content += f"""
                        <div class="detail-row">
                            <button class="preview-btn" onclick="previewFile('{html.escape(export_path, quote=True)}', '{html.escape(uxml_name, quote=True)}', 'xml')">🔍 Preview XML</button>
                        </div>
"""

        html_content += """                    </div>
                </div>
"""

    html_content += """            </div>
        </div>

        <!-- Stylesheets Tab -->
        <div id="stylesheets" class="tab-content">
            <div class="item-grid" id="stylesheets-grid">
"""

    # Generate Stylesheets
    for sheet_name, sheet_data in sorted(stylesheets.items()):
        bundle = sheet_data.get("bundle", "")
        variables_defined = sheet_data.get("variables_defined", [])
        classes_defined = sheet_data.get("classes_defined", [])
        export_path = sheet_data.get("export_path", "")

        html_content += f"""
                <div class="item-card" data-name="{html.escape(sheet_name.lower())}" data-type="stylesheet" data-export="{html.escape(export_path)}">
                    <div class="item-header">
                        <div class="item-name">{html.escape(sheet_name)}
                            <button class="copy-btn" onclick="copyToClipboard('{html.escape(sheet_name, quote=True)}')">📋</button>
                        </div>
                        <div class="item-badge">{html.escape(bundle)}</div>
                    </div>
                    <div class="item-details">
"""

        if variables_defined:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Variables ({len(variables_defined)}):</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for var in variables_defined[:15]:
                html_content += f'                                    <div class="tag">{html.escape(var)}</div>\n'
            if len(variables_defined) > 15:
                html_content += f'                                    <div class="tag">+{len(variables_defined) - 15} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if classes_defined:
            html_content += f"""
                        <div class="detail-row">
                            <div class="detail-label">Classes ({len(classes_defined)}):</div>
                            <div class="detail-value">
                                <div class="tag-list">
"""
            for cls in classes_defined[:15]:
                html_content += f'                                    <div class="tag">{html.escape(cls)}</div>\n'
            if len(classes_defined) > 15:
                html_content += f'                                    <div class="tag">+{len(classes_defined) - 15} more</div>\n'
            html_content += """                                </div>
                            </div>
                        </div>
"""

        if export_path:
            html_content += f"""
                        <div class="detail-row">
                            <button class="preview-btn" onclick="previewFile('{html.escape(export_path, quote=True)}', '{html.escape(sheet_name, quote=True)}', 'css')">🔍 Preview CSS</button>
                        </div>
"""

        html_content += """                    </div>
                </div>
"""

    html_content += """            </div>
        </div>
    </div>

    <!-- Preview Overlay -->
    <div id="previewOverlay" class="preview-overlay">
        <div class="preview-content">
            <div class="preview-header">
                <div class="preview-title" id="previewTitle"></div>
                <button class="preview-close" onclick="closePreview()">×</button>
            </div>
            <div class="preview-body" id="previewBody">
                <div class="preview-loading">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        // Get DOM elements first
        const searchBox = document.getElementById('searchBox');
        const allCards = document.querySelectorAll('.item-card');
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');

        // Tab switching
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;

                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(tc => tc.classList.remove('active'));

                tab.classList.add('active');
                document.getElementById(tabId).classList.add('active');

                // Re-apply search filter
                searchBox.dispatchEvent(new Event('input'));
            });
        });

        // Search functionality

        searchBox.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            let visibleCount = 0;

            allCards.forEach(card => {
                const name = card.dataset.name;
                const isInActiveTab = card.closest('.tab-content').classList.contains('active');
                const matches = name.includes(query);

                if (isInActiveTab) {
                    card.classList.toggle('hidden', !matches);
                    if (matches) visibleCount++;
                }
            });
        });

        // Copy to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Visual feedback
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✓';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 1000);
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        }

        // Expand/collapse details
        function toggleExpand(btn) {
            const content = btn.nextElementSibling;
            const isExpanded = content.classList.contains('show');

            if (isExpanded) {
                content.classList.remove('show');
                btn.textContent = btn.textContent.replace('Hide', 'Show');
            } else {
                content.classList.add('show');
                btn.textContent = btn.textContent.replace('Show', 'Hide');
            }
        }

        // Keyboard navigation
        searchBox.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchBox.value = '';
                searchBox.dispatchEvent(new Event('input'));
            }
        });

        // Preview functionality
        function previewFile(exportPath, fileName, type) {
            const overlay = document.getElementById('previewOverlay');
            const title = document.getElementById('previewTitle');
            const body = document.getElementById('previewBody');

            overlay.classList.add('show');
            title.textContent = fileName;
            body.innerHTML = '<div class="preview-loading">Loading preview...</div>';

            // Construct the full path relative to the HTML file
            // The exports folder is in the same directory as the HTML file
            const baseUrl = window.location.href.substring(0, window.location.href.lastIndexOf('/'));
            const fullPath = baseUrl + '/' + exportPath;

            console.log('Fetching file from:', fullPath);

            // Fetch the file content
            fetch(fullPath)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('File not found: ' + exportPath + ' (HTTP ' + response.status + ')');
                    }
                    return response.text();
                })
                .then(content => {
                    const highlighted = type === 'css' ? highlightCSS(content) : highlightXML(content);
                    body.innerHTML = '<pre class="preview-code">' + highlighted + '</pre>';
                })
                .catch(error => {
                    body.innerHTML = '<div class="preview-error">Error loading file: ' + escapeHtml(error.message) + '<br><br>Make sure you are viewing this file via a web server (e.g., python -m http.server) or the browser may block local file access.</div>';
                    console.error('Preview error:', error);
                });
        }

        function closePreview() {
            document.getElementById('previewOverlay').classList.remove('show');
        }

        // Close preview with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closePreview();
            }
        });

        // Close preview when clicking outside content
        document.getElementById('previewOverlay').addEventListener('click', (e) => {
            if (e.target.id === 'previewOverlay') {
                closePreview();
            }
        });

        // Syntax highlighting for CSS
        function highlightCSS(code) {
            return escapeHtml(code)
                .replace(/(\.[-\w]+|#[-\w]+|\*|[a-zA-Z][\w-]*)/g, '<span class="css-selector">$1</span>')
                .replace(/([-\w]+)(?=\s*:)/g, '<span class="css-property">$1</span>')
                .replace(/:\s*([^;\n]+)/g, ': <span class="css-value">$1</span>');
        }

        // Syntax highlighting for XML
        function highlightXML(code) {
            return escapeHtml(code)
                .replace(/(&lt;\/?)([-\w:]+)/g, '$1<span class="xml-tag">$2</span>')
                .replace(/\s([-\w:]+)=/g, ' <span class="xml-attribute">$1</span>=')
                .replace(/=&quot;([^&]*?)&quot;/g, '=<span class="xml-string">&quot;$1&quot;</span>');
        }

        // HTML escape helper
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""

    # Write HTML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding='utf-8')

    print(f"✓ Generated HTML explorer: {output_path}")
    print(f"  Open in browser: file://{output_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML explorer for CSS ↔ UXML catalog"
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
        default=Path("extracted_sprites/css_uxml_explorer.html"),
        help="Output HTML file path (default: extracted_sprites/css_uxml_explorer.html)"
    )
    parser.add_argument(
        "--title",
        default="FM CSS & UXML Explorer",
        help="Title for the HTML page"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input catalog not found: {args.input}")
        return 1

    generate_html_explorer(args.input, args.output, args.title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
