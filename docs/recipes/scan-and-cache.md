# Scan and transparent cache

Scan (optional) explores which variables and selectors appear and where. A transparent cache can speed up patching by pre-filtering candidate assets; it’s never required and is silent by default.

Explore with scan

- python -m src.cli.main scan --bundle /path/to/bundle_or_dir --out build/scan --export-uss

This writes:
- build/scan/<bundle-stem>/bundle_index.json
- build/scan/<bundle-stem>/scan_uss/*.uss (if --export-uss)

Transparent scan cache (patch)

- When patching a known skin (has config.json), we store an index under .cache/skins/<skin>/<bundle-stem>.index.json with bundle fingerprint.
- If available, it’s used to prefilter candidate assets for patching based on your current CSS (variables and selector overrides).
- It never disables patching logic; if no candidates are found, we fall back to scanning all assets safely.

Controls

- --no-scan-cache: don’t use the cache (scan all assets during patching)
- --refresh-scan-cache: refresh cache before patching
