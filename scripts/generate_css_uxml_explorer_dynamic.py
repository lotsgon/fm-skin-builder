#!/usr/bin/env python3
"""Generate a dynamic HTML explorer that loads catalog data via JavaScript.

Creates a lightweight HTML interface that fetches the catalog JSON at runtime
and renders data on-demand, avoiding massive static HTML files.

Usage:
    python scripts/generate_css_uxml_explorer_dynamic.py --input extracted_sprites/css_uxml_catalog.json --output extracted_sprites/css_uxml_explorer.html
"""

import argparse
import json
import sys
from pathlib import Path
import html


def generate_dynamic_html_explorer(catalog_path: Path, output_path: Path, title: str = "CSS & UXML Explorer"):
    """Generate a lightweight HTML explorer that loads catalog via JavaScript."""

    # Calculate relative path from HTML to catalog JSON
    try:
        catalog_rel_path = catalog_path.relative_to(output_path.parent)
    except ValueError:
        # If they're not in related paths, use the filename only
        catalog_rel_path = catalog_path.name

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
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            color: white;
        }}
        .header p {{
            font-size: 1.1rem;
            opacity: 0.95;
            color: white;
        }}
        .controls {{
            margin-bottom: 20px;
        }}
        .search-box {{
            width: 100%;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #2a2a2a;
            color: #e0e0e0;
            outline: none;
            transition: all 0.3s ease;
        }}
        .search-box:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            flex-wrap: wrap;
        }}
        .tab {{
            padding: 12px 24px;
            background: transparent;
            border: none;
            color: #999;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
        }}
        .tab:hover {{
            color: #e0e0e0;
            background: rgba(102, 126, 234, 0.1);
        }}
        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat {{
            padding: 15px 20px;
            background: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #333;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 14px;
            color: #999;
            margin-top: 5px;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .items-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
        }}
        .item-card {{
            background: #2a2a2a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            transition: all 0.3s ease;
        }}
        .item-card:hover {{
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}
        .item-card.hidden {{
            display: none;
        }}
        .item-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .item-name {{
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            color: #667eea;
            font-weight: 600;
        }}
        .copy-btn, .preview-btn, .expand-btn {{
            background: #333;
            border: 1px solid #444;
            color: #e0e0e0;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s ease;
        }}
        .copy-btn:hover, .preview-btn:hover, .expand-btn:hover {{
            background: #667eea;
            border-color: #667eea;
        }}
        .tag {{
            display: inline-block;
            padding: 4px 8px;
            background: #333;
            border-radius: 4px;
            font-size: 11px;
            color: #999;
            margin-right: 5px;
            margin-bottom: 5px;
        }}
        .details {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #333;
            font-size: 12px;
            color: #999;
        }}
        .preview-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            padding: 20px;
        }}
        .preview-overlay.show {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .preview-content {{
            background: #1a1a1a;
            border: 2px solid #667eea;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90%;
            width: 1000px;
            display: flex;
            flex-direction: column;
        }}
        .preview-header {{
            padding: 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .preview-title {{
            font-size: 18px;
            font-weight: 600;
            color: #667eea;
        }}
        .preview-close {{
            background: #f44336;
            color: white;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }}
        .preview-close:hover {{
            background: #d32f2f;
        }}
        .preview-body {{
            padding: 20px;
            overflow: auto;
            flex: 1;
        }}
        .preview-code {{
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre;
            color: #e0e0e0;
        }}
        .preview-loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        .css-property {{ color: #9cdcfe; }}
        .css-value {{ color: #ce9178; }}
        .css-selector {{ color: #d7ba7d; }}
        .xml-tag {{ color: #4ec9b0; }}
        .xml-attribute {{ color: #9cdcfe; }}
        .xml-string {{ color: #ce9178; }}

        /* Enhanced XML viewer */
        .xml-viewer {{
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.8;
            color: #e0e0e0;
        }}
        .xml-line {{
            position: relative;
            padding-left: 50px;
            white-space: pre;
        }}
        .xml-line::before {{
            content: attr(data-line);
            position: absolute;
            left: 0;
            width: 40px;
            text-align: right;
            color: #666;
            font-size: 11px;
            padding-right: 10px;
            user-select: none;
            border-right: 1px solid #333;
        }}
        .xml-line:hover {{
            background: rgba(102, 126, 234, 0.1);
        }}
        .xml-empty {{
            min-height: 1.8em;
        }}

        /* Element type specific colors */
        .xml-tag.si-element {{ color: #c586c0; font-weight: 600; }}
        .xml-tag.binding-element {{ color: #dcdcaa; font-weight: 600; }}
        .xml-tag.visual-element {{ color: #4ec9b0; }}
        .loading {{
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #999;
        }}
        .error {{
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #f44336;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 {html.escape(title)}</h1>
            <p>Search and explore CSS variables, classes, UXML files, and their relationships in Football Manager.</p>
        </div>

        <div class="controls">
            <input type="text" class="search-box" id="searchBox" placeholder="Search by name (e.g., '--primary', '.green', 'MainMenu')..." autofocus>
        </div>

        <div class="stats" id="stats">
            <div class="stat">
                <div class="stat-value" id="varCount">-</div>
                <div class="stat-label">CSS Variables</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="classCount">-</div>
                <div class="stat-label">CSS Classes</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="uxmlCount">-</div>
                <div class="stat-label">UXML Files</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="sheetCount">-</div>
                <div class="stat-label">Stylesheets</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="componentCount">-</div>
                <div class="stat-label">Custom Components</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="templateCount">-</div>
                <div class="stat-label">UXML Templates</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="variables">Variables</button>
            <button class="tab" data-tab="classes">Classes</button>
            <button class="tab" data-tab="uxml">UXML Files</button>
            <button class="tab" data-tab="stylesheets">Stylesheets</button>
            <button class="tab" data-tab="components">Components</button>
            <button class="tab" data-tab="templates">Templates</button>
        </div>

        <div id="content">
            <div class="loading">Loading catalog data...</div>
        </div>
    </div>

    <div class="preview-overlay" id="previewOverlay">
        <div class="preview-content">
            <div class="preview-header">
                <div class="preview-title" id="previewTitle">Preview</div>
                <button class="preview-close" onclick="closePreview()">×</button>
            </div>
            <div class="preview-body" id="previewBody">
                <div class="preview-loading">Loading preview...</div>
            </div>
        </div>
    </div>

    <script>
        // Configuration
        const CATALOG_URL = '{catalog_rel_path}';
        const BASE_URL = window.location.href.substring(0, window.location.href.lastIndexOf('/'));

        // Global state
        let catalog = null;
        let currentTab = 'variables';
        let searchQuery = '';

        // Get DOM elements
        const searchBox = document.getElementById('searchBox');
        const contentDiv = document.getElementById('content');
        const tabs = document.querySelectorAll('.tab');

        // Load catalog on page load
        window.addEventListener('DOMContentLoaded', async () => {{
            console.log('Starting catalog load from:', CATALOG_URL);
            contentDiv.innerHTML = '<div class="loading">Loading catalog data (this may take a few seconds for large catalogs)...</div>';

            try {{
                console.log('Fetching catalog...');
                const response = await fetch(CATALOG_URL);
                console.log('Fetch response:', response.status, response.statusText);

                if (!response.ok) {{
                    throw new Error(`Failed to load catalog: ${{response.status}} ${{response.statusText}}`);
                }}

                console.log('Parsing JSON...');
                catalog = await response.json();
                console.log('Catalog loaded successfully:', {{
                    variables: Object.keys(catalog.css_variables || {{}}).length,
                    classes: Object.keys(catalog.css_classes || {{}}).length,
                    uxml: Object.keys(catalog.uxml_files || {{}}).length,
                    stylesheets: Object.keys(catalog.stylesheets || {{}}).length,
                    components: Object.keys(catalog.components || {{}}).length,
                    templates: Object.keys(catalog.templates || {{}}).length
                }});

                // Update stats
                document.getElementById('varCount').textContent = Object.keys(catalog.css_variables || {{}}).length;
                document.getElementById('classCount').textContent = Object.keys(catalog.css_classes || {{}}).length;
                document.getElementById('uxmlCount').textContent = Object.keys(catalog.uxml_files || {{}}).length;
                document.getElementById('sheetCount').textContent = Object.keys(catalog.stylesheets || {{}}).length;

                // Count custom components (SI.* and FM.*)
                const customComponents = Object.values(catalog.components || {{}}).filter(c => c.is_custom);
                document.getElementById('componentCount').textContent = customComponents.length;

                // Count templates
                document.getElementById('templateCount').textContent = Object.keys(catalog.templates || {{}}).length;

                // Render initial view
                console.log('Rendering initial view...');
                renderTab('variables');
                console.log('Ready!');
            }} catch (error) {{
                contentDiv.innerHTML = `<div class="error">Error loading catalog: ${{error.message}}<br><br>Check the browser console for details.</div>`;
                console.error('Failed to load catalog:', error);
                console.error('Catalog URL:', CATALOG_URL);
                console.error('Current location:', window.location.href);
            }}
        }});

        // Tab switching
        tabs.forEach(tab => {{
            tab.addEventListener('click', () => {{
                const tabId = tab.dataset.tab;
                currentTab = tabId;

                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                renderTab(tabId);
            }});
        }});

        // Search functionality
        searchBox.addEventListener('input', (e) => {{
            searchQuery = e.target.value.toLowerCase();
            renderTab(currentTab);
        }});

        // Keyboard navigation
        searchBox.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                searchBox.value = '';
                searchQuery = '';
                renderTab(currentTab);
            }}
        }});

        // Render tab content
        function renderTab(tabName) {{
            if (!catalog) return;

            let html = '';

            switch(tabName) {{
                case 'variables':
                    html = renderVariables();
                    break;
                case 'classes':
                    html = renderClasses();
                    break;
                case 'uxml':
                    html = renderUXML();
                    break;
                case 'stylesheets':
                    html = renderStylesheets();
                    break;
                case 'components':
                    html = renderComponents();
                    break;
                case 'templates':
                    html = renderTemplates();
                    break;
            }}

            contentDiv.innerHTML = html;
        }}

        // Render variables
        function renderVariables() {{
            const variables = catalog.css_variables || {{}};
            const filtered = filterItems(variables);

            if (filtered.length === 0) {{
                return '<div class="loading">No variables found matching your search.</div>';
            }}

            let html = '<div class="items-grid">';
            for (const [name, data] of filtered) {{
                const sheets = data.used_in_stylesheets || [];
                html += `
                    <div class="item-card" data-name="${{escapeHtml(name)}}">
                        <div class="item-header">
                            <div class="item-name">${{escapeHtml(name)}}</div>
                            <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                        </div>
                        <div class="details">
                            <strong>Used in:</strong> ${{sheets.length}} stylesheet(s)
                            <div>${{sheets.map(s => `<span class="tag">${{escapeHtml(s)}}</span>`).join('')}}</div>
                        </div>
                    </div>
                `;
            }}
            html += '</div>';
            return html;
        }}

        // Render classes
        function renderClasses() {{
            const classes = catalog.css_classes || {{}};
            const filtered = filterItems(classes);

            if (filtered.length === 0) {{
                return '<div class="loading">No classes found matching your search.</div>';
            }}

            let html = '<div class="items-grid">';
            for (const [name, data] of filtered) {{
                const uxmlFiles = data.used_in_uxml || [];
                const sheets = data.defined_in || [];
                html += `
                    <div class="item-card" data-name="${{escapeHtml(name)}}">
                        <div class="item-header">
                            <div class="item-name">${{escapeHtml(name)}}</div>
                            <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                        </div>
                        <div class="details">
                            <strong>Defined in:</strong> ${{sheets.length}} stylesheet(s)<br>
                            <strong>Used in:</strong> ${{uxmlFiles.length}} UXML file(s)
                        </div>
                    </div>
                `;
            }}
            html += '</div>';
            return html;
        }}

        // Render UXML files
        function renderUXML() {{
            const uxmlFiles = catalog.uxml_files || {{}};
            const filtered = filterItems(uxmlFiles);

            if (filtered.length === 0) {{
                return '<div class="loading">No UXML files found matching your search.</div>';
            }}

            let html = '<div class="items-grid">';
            for (const [name, data] of filtered) {{
                const exportPath = data.export_path || '';
                const classes = data.classes_used || [];
                html += `
                    <div class="item-card" data-name="${{escapeHtml(name)}}">
                        <div class="item-header">
                            <div class="item-name">${{escapeHtml(name)}}</div>
                            <div>
                                <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                                ${{exportPath ? `<button class="preview-btn" onclick="previewFile('${{escapeHtml(exportPath, true)}}', '${{escapeHtml(name, true)}}', 'xml')">🔍 Preview</button>` : ''}}
                            </div>
                        </div>
                        <div class="details">
                            <strong>Classes:</strong> ${{classes.length}}
                            <div>${{classes.slice(0, 10).map(c => `<span class="tag">${{escapeHtml(c)}}</span>`).join('')}}${{classes.length > 10 ? '<span class="tag">...</span>' : ''}}</div>
                        </div>
                    </div>
                `;
            }}
            html += '</div>';
            return html;
        }}

        // Render stylesheets
        function renderStylesheets() {{
            const sheets = catalog.stylesheets || {{}};
            const filtered = filterItems(sheets);

            if (filtered.length === 0) {{
                return '<div class="loading">No stylesheets found matching your search.</div>';
            }}

            let html = '<div class="items-grid">';
            for (const [name, data] of filtered) {{
                const exportPath = data.export_path || '';
                const classes = data.classes_defined || [];
                html += `
                    <div class="item-card" data-name="${{escapeHtml(name)}}">
                        <div class="item-header">
                            <div class="item-name">${{escapeHtml(name)}}</div>
                            <div>
                                <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                                ${{exportPath ? `<button class="preview-btn" onclick="previewFile('${{escapeHtml(exportPath, true)}}', '${{escapeHtml(name, true)}}', 'css')">🔍 Preview</button>` : ''}}
                            </div>
                        </div>
                        <div class="details">
                            <strong>Classes:</strong> ${{classes.length}}
                            <div>${{classes.slice(0, 10).map(c => `<span class="tag">${{escapeHtml(c)}}</span>`).join('')}}${{classes.length > 10 ? '<span class="tag">...</span>' : ''}}</div>
                        </div>
                    </div>
                `;
            }}
            html += '</div>';
            return html;
        }}

        // Render components
        function renderComponents() {{
            const components = catalog.components || {{}};
            const filtered = filterItems(components);

            if (filtered.length === 0) {{
                return '<div class="loading">No components found matching your search.</div>';
            }}

            // Filter to only show custom components (SI.* and FM.*)
            const customComponents = filtered.filter(([name, data]) => data.is_custom);

            if (customComponents.length === 0) {{
                return '<div class="loading">No custom components found matching your search.</div>';
            }}

            // Group by namespace
            const byNamespace = {{}};
            for (const [name, data] of customComponents) {{
                const namespace = data.namespace || 'Unknown';
                if (!byNamespace[namespace]) {{
                    byNamespace[namespace] = [];
                }}
                byNamespace[namespace].push([name, data]);
            }}

            let html = '';

            // Render namespace summary
            html += '<div style="margin-bottom: 20px; padding: 15px; background: #2a2a2a; border-radius: 8px; border: 1px solid #333;">';
            html += '<h3 style="margin-bottom: 10px; color: #667eea;">Component Namespaces</h3>';
            html += '<div style="display: flex; gap: 15px; flex-wrap: wrap;">';
            for (const [namespace, items] of Object.entries(byNamespace).sort()) {{
                html += `<div class="tag" style="font-size: 14px; padding: 8px 12px;">${{escapeHtml(namespace)}} (${{items.length}})</div>`;
            }}
            html += '</div></div>';

            // Render components grouped by namespace
            for (const [namespace, items] of Object.entries(byNamespace).sort()) {{
                html += `<h3 style="color: #667eea; margin: 20px 0 15px 0; font-size: 18px; border-bottom: 2px solid #333; padding-bottom: 8px;">${{escapeHtml(namespace)}}</h3>`;
                html += '<div class="items-grid">';

                for (const [name, data] of items.sort((a, b) => a[0].localeCompare(b[0]))) {{
                    const uxmlFiles = data.used_in_uxml || [];
                    const shortName = name.split('.').pop(); // Get just the class name
                    html += `
                        <div class="item-card" data-name="${{escapeHtml(name)}}">
                            <div class="item-header">
                                <div class="item-name" style="font-size: 16px;">${{escapeHtml(shortName)}}</div>
                                <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                            </div>
                            <div class="details">
                                <div style="font-size: 12px; color: #999; margin-bottom: 8px;">${{escapeHtml(name)}}</div>
                                <strong>Used in:</strong> ${{uxmlFiles.length}} UXML file(s)
                                <div style="max-height: 150px; overflow-y: auto; margin-top: 8px;">
                                    ${{uxmlFiles.slice(0, 20).map(f => `<span class="tag" style="cursor: pointer; font-size: 11px;" onclick="showUXMLFile('${{escapeHtml(f, true)}}')">${{escapeHtml(f)}}</span>`).join('')}}
                                    ${{uxmlFiles.length > 20 ? `<span class="tag">... and ${{uxmlFiles.length - 20}} more</span>` : ''}}
                                </div>
                            </div>
                        </div>
                    `;
                }}
                html += '</div>';
            }}

            return html;
        }}

        // Helper function to show a specific UXML file
        function showUXMLFile(fileName) {{
            // Switch to UXML tab and search for the file
            searchBox.value = fileName;
            searchQuery = fileName.toLowerCase();
            currentTab = 'uxml';

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelector('[data-tab="uxml"]').classList.add('active');

            renderTab('uxml');
        }}

        // Render templates (UXML composition)
        function renderTemplates() {{
            const templates = catalog.templates || {{}};
            const filtered = filterItems(templates);

            if (filtered.length === 0) {{
                return '<div class="loading">No templates found matching your search.</div>';
            }}

            // Sort by usage count
            const sortedTemplates = filtered.sort((a, b) => {{
                const aUsage = a[1].used_in_uxml?.length || 0;
                const bUsage = b[1].used_in_uxml?.length || 0;
                return bUsage - aUsage;
            }});

            let html = '';

            // Summary
            html += '<div style="margin-bottom: 20px; padding: 15px; background: #2a2a2a; border-radius: 8px; border: 1px solid #333;">';
            html += '<h3 style="margin-bottom: 10px; color: #667eea;">UXML Templates (Reusable Components)</h3>';
            html += '<p style="color: #999; line-height: 1.6;">These are UXML files that are included in other UXML files, similar to React component imports. ';
            html += 'They enable composition and reusability across the UI.</p>';
            html += '</div>';

            // Render templates
            html += '<div class="items-grid">';
            for (const [name, data] of sortedTemplates) {{
                const uxmlFiles = data.used_in_uxml || [];
                html += `
                    <div class="item-card" data-name="${{escapeHtml(name)}}">
                        <div class="item-header">
                            <div class="item-name" style="font-size: 16px; color: #667eea;">${{escapeHtml(name)}}</div>
                            <button class="copy-btn" onclick="copyToClipboard('${{escapeHtml(name, true)}}')">📋</button>
                        </div>
                        <div class="details">
                            <strong>Used in:</strong> ${{uxmlFiles.length}} file(s)
                            <div style="max-height: 200px; overflow-y: auto; margin-top: 8px;">
                                ${{uxmlFiles.slice(0, 25).map(f => `<span class="tag" style="cursor: pointer; font-size: 11px;" onclick="showUXMLFile('${{escapeHtml(f, true)}}')">${{escapeHtml(f)}}</span>`).join('')}}
                                ${{uxmlFiles.length > 25 ? `<span class="tag">... and ${{uxmlFiles.length - 25}} more</span>` : ''}}
                            </div>
                        </div>
                    </div>
                `;
            }}
            html += '</div>';

            return html;
        }}

        // Filter items by search query
        function filterItems(items) {{
            const entries = Object.entries(items);
            if (!searchQuery) {{
                return entries;
            }}
            return entries.filter(([name]) => name.toLowerCase().includes(searchQuery));
        }}

        // Copy to clipboard
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✓';
                setTimeout(() => {{
                    btn.textContent = originalText;
                }}, 1000);
            }}).catch(err => {{
                console.error('Failed to copy:', err);
            }});
        }}

        // Preview file
        async function previewFile(exportPath, fileName, type) {{
            const overlay = document.getElementById('previewOverlay');
            const title = document.getElementById('previewTitle');
            const body = document.getElementById('previewBody');

            overlay.classList.add('show');
            title.textContent = fileName;
            body.innerHTML = '<div class="preview-loading">Loading preview...</div>';

            try {{
                const response = await fetch(BASE_URL + '/' + exportPath);
                if (!response.ok) {{
                    throw new Error(`File not found: ${{exportPath}} (HTTP ${{response.status}})`);
                }}
                const content = await response.text();

                let highlighted = '';
                if (type === 'css') {{
                    highlighted = highlightCSS(content);
                }} else if (type === 'xml') {{
                    highlighted = highlightXML(content);
                }} else {{
                    highlighted = escapeHtml(content);
                }}

                body.innerHTML = `<pre class="preview-code">${{highlighted}}</pre>`;
            }} catch (error) {{
                body.innerHTML = `<div class="error">Error loading file: ${{error.message}}</div>`;
                console.error('Preview error:', error);
            }}
        }}

        // Close preview
        function closePreview() {{
            document.getElementById('previewOverlay').classList.remove('show');
        }}

        // Syntax highlighting for CSS
        function highlightCSS(code) {{
            return escapeHtml(code)
                .replace(/(\.[-\\w]+|#[-\\w]+|\\*|[a-zA-Z][\\w-]*)/g, '<span class="css-selector">$1</span>')
                .replace(/([-\\w]+)(?=\\s*:)/g, '<span class="css-property">$1</span>')
                .replace(/:\\s*([^;\\n]+)/g, ': <span class="css-value">$1</span>');
        }}

        // Enhanced syntax highlighting for XML with collapsible elements
        function highlightXML(code) {{
            const lines = code.split('\\n');
            let result = '<div class="xml-viewer">';
            let lineNum = 1;

            lines.forEach(line => {{
                const indent = line.match(/^\\s*/)[0].length;
                const trimmed = line.trim();

                if (!trimmed) {{
                    result += '<div class="xml-line xml-empty"></div>';
                    return;
                }}

                // Detect element types for better highlighting
                let elementType = '';
                const tagMatch = trimmed.match(/<([\\w:]+)/);
                if (tagMatch) {{
                    const tag = tagMatch[1];
                    if (tag.startsWith('SI')) elementType = 'si-element';
                    else if (tag.startsWith('Binding')) elementType = 'binding-element';
                    else if (tag === 'VisualElement') elementType = 'visual-element';
                }}

                // Escape and highlight
                let highlighted = escapeHtml(line)
                    .replace(/(&lt;\\/?)([\\w:-]+)/g, function(match, p1, p2) {{
                        return p1 + '<span class="xml-tag ' + elementType + '">' + p2 + '</span>';
                    }})
                    .replace(/\\s([\\w:-]+)=/g, ' <span class="xml-attribute">$1</span>=')
                    .replace(/=&quot;([^&]*?)&quot;/g, '=<span class="xml-string">&quot;$1&quot;</span>');

                result += `<div class="xml-line" data-line="${{lineNum}}">${{highlighted}}</div>`;
                lineNum++;
            }});

            result += '</div>';
            return result;
        }}

        // HTML escape helper
        function escapeHtml(text, forAttr = false) {{
            const div = document.createElement('div');
            div.textContent = text;
            let escaped = div.innerHTML;
            if (forAttr) {{
                escaped = escaped.replace(/'/g, '&#39;');
            }}
            return escaped;
        }}

        // Close preview on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closePreview();
            }}
        }});

        // Close preview on overlay click
        document.getElementById('previewOverlay').addEventListener('click', (e) => {{
            if (e.target.id === 'previewOverlay') {{
                closePreview();
            }}
        }});
    </script>
</body>
</html>
"""

    # Write HTML file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding='utf-8')

    print(f"✓ Generated dynamic HTML explorer: {output_path}")
    print(f"  Catalog: {catalog_path}")
    print(f"  Open in browser: file://{output_path.absolute()}")
    print(f"\n  Note: This HTML requires a web server (e.g., python -m http.server)")
    print(f"  The static HTML approach is only suitable for small catalogs.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a dynamic HTML explorer for CSS ↔ UXML catalog"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input catalog JSON file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output HTML file"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="CSS & UXML Explorer",
        help="Page title"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    generate_dynamic_html_explorer(args.input, args.output, args.title)


if __name__ == "__main__":
    main()
