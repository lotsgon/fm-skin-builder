# Conflict surfacing summary

When a selector/property override touches multiple StyleSheet assets, the summary includes a short section, for example:

- Selector overrides affecting multiple assets:
  - .green / color: 3 assets

Notes

- This is informational; we still patch all applicable assets by default.
- Use targeting hints to narrow scope if needed (see targeting-hints.md).
- Use dry-run first to preview impact.
