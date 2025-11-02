# Skin Config Format (Versioned)

Example (`schema_version` required):
```json
{
  "schema_version": 1,
  "name": "Gold Theme",
  "target_bundle": "fm_base.bundle",
  "output_bundle": "fm_base.bundle",
  "overrides": {
    "ui/skins/base/colours/FMColours.uss": "colours/FMColours.uss"
  },
  "description": "Example theme"
}
```

## Caching
- Cached at `.cache/skins/<skin>/<hash>.json` based on file mtime + content hash.
