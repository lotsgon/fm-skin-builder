# Change a CSS variable color

Goal: Update all places that use a given CSS variable (strict mapping) to a new color.

Minimal steps

- Put your variable in your skin CSS/USS:
  - skins/your_skin/colours/base.uss:
    :root { --primary: #112233; }

- Patch (infers bundle from skin config):
  - python -m fm_skin_builder.cli.main patch skins/your_skin --out build

What it does

- Looks for StyleSheet rules where a color slot uses both a variable reference (strings type 3/10) and a color reference (colors type 4) at the same index.
- If that variable is in your CSS, it updates the color to your hex value.

Tips

- Change-aware: nothing is written if there are no differences.
- Dry-run and debug exports are handy while iterating:
  - python -m fm_skin_builder.cli.main patch skins/your_skin --out build --dry-run
  - python -m fm_skin_builder.cli.main patch skins/your_skin --out build --debug-export
