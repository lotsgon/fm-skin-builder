# 🗺️ Roadmap Hints

**Phase 1 – Core CLI**

- Implement `fm-skin build` to compile skin folders into bundles
- Add config validation and clean error reporting
- Provide logging with color + verbosity flags

**Phase 2 – Swapper / Verification**

- Automatic backup and restore of FM bundles
- Cross-platform support (macOS / Linux / Windows)
- Optional verification using `fs_usage`, `inotify`, or ProcMon

**Phase 3 – GUI Manager**

- Visual skin selector + apply button
- Live logs inside GUI window
- Configurable paths to FM install

**Phase 4 – Web Preview**

- Electron / Next.js front-end consuming the same backend API
- Theming preview (color palettes, fonts, UI backgrounds)

**Ongoing**

- Unit tests for each module
- Documentation for plugin / skin schema
