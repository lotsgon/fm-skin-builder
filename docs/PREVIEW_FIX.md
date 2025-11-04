# Preview Feature - Quick Fix Guide

## Issue: "Error loading file: Failed to fetch"

This error occurs because browsers block file access when opening HTML files directly using the `file://` protocol for security reasons.

## Solution: Use a Web Server

The preview feature requires serving the HTML file through a web server. Here's how:

### Option 1: Python HTTP Server (Easiest)

```bash
# Navigate to the extracted_sprites directory
cd extracted_sprites

# Start the server
python -m http.server 8000

# Server will output:
# Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Then open in your browser:
- **URL**: http://localhost:8000/css_uxml_explorer_preview_fixed.html

### Option 2: VS Code Live Server Extension

1. Install "Live Server" extension in VS Code
2. Right-click `css_uxml_explorer_preview_fixed.html`
3. Select "Open with Live Server"

### Option 3: Node.js http-server

```bash
# Install globally
npm install -g http-server

# Run from extracted_sprites directory
cd extracted_sprites
http-server -p 8000
```

Then open: http://localhost:8000/css_uxml_explorer_preview_fixed.html

## Testing the Preview

Once the server is running and you've opened the HTML:

### Test 1: Preview a Stylesheet

1. Click the **Stylesheets** tab
2. Find "IGEStyles" or "SIStyles"
3. Click **🔍 Preview CSS**
4. You should see syntax-highlighted CSS

If it works, you'll see:
```css
.ige-field {
  width: var(space-between);
  border-color: space-between;
  background-color: --colours-alpha-transparent-0;
}
```

### Test 2: Preview a UXML File

1. Click the **UXML Files** tab
2. Search for "CalendarTool"
3. Click **🔍 Preview XML**
4. You should see formatted XML

If it works, you'll see:
```xml
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <UXML>
        <BindingRoot class="base-template-grow calendar-button-group">
            ...
        </BindingRoot>
    </UXML>
```

## Troubleshooting

### Still Getting "Failed to fetch"?

**Check the browser console** (F12 → Console tab) for detailed errors:

1. **CORS Error**: Make sure you're using a web server, not opening the file directly
2. **404 Not Found**: Check that the `exports/` directory exists in the same folder as the HTML
3. **Path Issues**: Verify the export paths in the catalog JSON

### Verify File Structure

Your directory should look like this:
```
extracted_sprites/
├── css_uxml_catalog_test.json
├── css_uxml_explorer_preview_fixed.html
└── exports/
    ├── uss/
    │   ├── IGEStyles.uss
    │   ├── SIStyles.uss
    │   └── ...
    └── uxml/
        ├── CalendarTool.uxml
        ├── AboutClubCard.uxml
        └── ...
```

### Test Direct File Access

From the extracted_sprites directory, test if you can fetch files:

```bash
# Test USS file
curl http://localhost:8000/exports/uss/IGEStyles.uss | head -10

# Test UXML file
curl http://localhost:8000/exports/uxml/CalendarTool.uxml
```

If these work, the preview should work in the browser.

### Check Server Logs

The Python HTTP server shows all requests. When you click preview, you should see:
```
127.0.0.1 - - [04/Nov/2025 15:25:17] "GET /exports/uss/IGEStyles.uss HTTP/1.1" 200 -
```

If you see 404 errors, the path is wrong.

## Why This Is Needed

### Browser Security

Browsers implement the **Same-Origin Policy** which prevents JavaScript from loading files from different origins. When you open an HTML file directly:

- Origin: `file:///path/to/file.html`
- Fetching: `file:///path/to/exports/file.uss`

Modern browsers block these requests because:
1. The `file://` protocol is treated as a special case
2. Each file has a different "origin" for security
3. This prevents malicious HTML from reading arbitrary files

### The Fix

Using a web server:
- Origin: `http://localhost:8000/file.html`
- Fetching: `http://localhost:8000/exports/file.uss`

Both requests come from the **same origin** (localhost:8000), so the browser allows it.

## Updated JavaScript

The fix includes better error messages and logging:

```javascript
function previewFile(exportPath, fileName, type) {
    // Construct path relative to HTML file location
    const baseUrl = window.location.href.substring(0, window.location.href.lastIndexOf('/'));
    const fullPath = baseUrl + '/' + exportPath;

    console.log('Fetching file from:', fullPath);

    fetch(fullPath)
        .then(response => {
            if (!response.ok) {
                throw new Error('File not found: ' + exportPath + ' (HTTP ' + response.status + ')');
            }
            return response.text();
        })
        .then(content => {
            // Display with syntax highlighting
        })
        .catch(error => {
            // Show helpful error message
        });
}
```

## Production Deployment

For production use, consider:

1. **Static Site Hosting**: Deploy to GitHub Pages, Netlify, or Vercel
2. **Integration**: Embed in an existing web application
3. **Desktop App**: Package with Electron for offline use

## Quick Start (TL;DR)

```bash
# 1. Navigate to directory
cd extracted_sprites

# 2. Start server
python -m http.server 8000

# 3. Open browser to:
http://localhost:8000/css_uxml_explorer_preview_fixed.html

# 4. Click preview buttons!
```

That's it! The preview feature should now work perfectly. 🎉

## Status

✅ **Web server running** on port 8000
✅ **Files accessible** at http://localhost:8000/exports/
✅ **HTML explorer** loaded in VS Code Simple Browser
✅ **Preview functionality** ready to test

**Next**: Try clicking **🔍 Preview CSS** or **🔍 Preview XML** buttons!
