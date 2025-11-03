## Components

- css_patcher
	- Parses CSS variables and selector overrides from a skin directory
	- Patches Unity StyleSheet assets inside bundles
	- Change-aware: only writes bundles/debug when changes occur
	- Supports `--patch-direct` (inlined literals) and `--dry-run` (no writes)
	- Optional debug export of original/patched `.uss` and JSON

- bundle_inspector
	- Scans bundle(s), builds an index of variables/selectors/usages
	- Optionally exports each StyleSheet as `.uss` for reference/diffing
	- Reports potential conflicts (same selector across multiple assets)

- SkinConfig / cache.py
	- Validates `config.json` (`schema_version`, `target_bundle`, etc.)
	- Caches parsed config under `.cache/skins/<skin>/<hash>.json`

- CLI
	- `patch`: CSS-first workflow; infers bundle from config or accepts `--bundle`
	- `scan`: Power-user tool to explore mappings; entirely optional

## Data flow (patch)

skin dir (CSS/USS) → collect variables + selector overrides →
load bundle(s) → detect/apply changes → write modified bundle(s) → optional debug exports

`--dry-run` follows the same discovery and change detection path but never writes files.

## Design principles

- Usability first: “write CSS, we do the rest”; no mapping files required
- Scan is optional; its artifacts are for exploration, not maintenance
- Prefer automatic, transparent caching when available
