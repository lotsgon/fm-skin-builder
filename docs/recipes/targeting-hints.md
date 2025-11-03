# Targeting hints (opt-in)

Power users can narrow patching scope with a simple hints.txt file placed in the skin or CSS directory. This never broadens scope—only narrows it—and defaults remain unchanged if no file is present.

Create skins/your_skin/hints.txt with any of these lines:

- asset: DialogStyles
- asset: CommonStyles, ExtraStyles
- selector: .green
- selector: .green color

Semantics

- asset: limits patching to the listed StyleSheet asset names.
- selector: limits selector/property overrides only:
  - selector: .green allows any property for the .green selector
  - selector: .green color allows only the color property for .green
- Selectors can be written with or without the leading dot.

Examples

1) Narrow to an asset while changing a variable

- colours/base.uss:
  :root { --primary: #123456; }
- hints.txt:
  asset: DialogStyles

2) Only override .green color across the whole bundle

- colours/overrides.uss:
  .green { color: #00D3E7; }
- hints.txt:
  selector: .green color

Dry-run to preview:

- python -m src.cli.main patch skins/your_skin --out build --dry-run
