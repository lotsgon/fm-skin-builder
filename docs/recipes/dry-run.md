# Preview without writing (dry-run)

Use dry-run to see what would change without writing modified bundles or debug files.

- python -m src.cli.main patch skins/your_skin --out build --dry-run

The summary includes:
- Stylesheets found
- Assets modified count
- Variables patched
- Direct colors patched (if --patch-direct is set)
- If multiple assets are affected by the same selector/property override, a short note listing them
