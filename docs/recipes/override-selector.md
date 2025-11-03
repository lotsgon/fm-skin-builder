# Override a selector/property color

Goal: Force a specific selector/property (e.g., .green color) to a new color wherever it appears.

Minimal steps

- Add a selector block in your skin CSS/USS:
  - skins/your_skin/colours/overrides.uss:
    .green { color: #00D3E7; }

- Patch:
  - python -m src.cli.main patch skins/your_skin --out build

What it does

- Finds rules matching the selector (supports class .name and name) and the specified property.
- Updates any color value (type 4) for that property to your hex.

Notes

- This can affect multiple StyleSheet assets; see the conflict surfacing recipe for what the summary logs show.
- You can narrow scope with opt-in targeting hints (see targeting-hints.md).
