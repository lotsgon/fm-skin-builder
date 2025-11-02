# FM26 Skin Builder

# Football Manager 2026 Skin Builder

This project is a **cross-platform toolkit** for creating and managing visual skin mods for _Football Manager 2026_.

## 🎯 Goals

- Safely replace or rebuild Unity `.bundle` files (no runtime code injection)
- Support config-driven `skins/<skin_name>/` folder layouts
- Provide both **CLI** (`fm-skin build …`) and future **GUI** tools
- Offer a non-destructive **swapper/launcher** that backs up originals
- Verify that Football Manager loads modified bundles via filesystem tracing

## 🧱 Architecture

src/

- core/ → bundle patching, config parsing, logging
- cli/ → command-line interface
- gui/ → future Tkinter / Qt GUI
- utils/ → helpers (paths, fs tracing, hashing)
- skins/ → holds user themes defined by `config.json`
- build/ is output for repacked bundles
- backups/ stores originals swapped out by the launcher

## 🧰 Technologies

- Python 3.11+
- UnityPy (planned) or similar for bundle manipulation
- Tkinter / Qt for local GUI
- GitHub Actions + pytest for CI

## 💡 Style & Guidelines

- PEP 8 + Black formatting
- Type hints throughout
- Verbose logging for debug
- Non-destructive design philosophy

Use this context when suggesting completions or documentation so Copilot understands the project purpose and conventions.
