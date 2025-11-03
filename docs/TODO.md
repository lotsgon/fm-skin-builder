# Development TODO

This is a living checklist for skin patching and bundle tooling.

- [x] Port standalone patcher into core module and CLI subcommand
- [x] Add CLI tests (patch), and unit tests for parser/patcher
- [x] Add sample skin `skins/test_skin` for docs and tests
- [x] Add `scan` subcommand to index bundles and export stylesheet maps
- [x] Add `--dry-run` patch mode to preview changes without writing files
- [ ] Optional targeting hints (advanced): allow pinning specific assets/selectors (low priority)
- [ ] Cache scan/index under `.cache/skins/<skin>/` and auto-reuse when available (transparent)
- [ ] Add conflict resolution strategies when the same selector appears in multiple assets
  - warn by default; support explicit asset pinning in mappings
- [ ] Add auto-discovery of standard install paths to locate bundles
- [ ] Docs: quick-start recipes (variables, selector overrides, dry-run, scan usage)
