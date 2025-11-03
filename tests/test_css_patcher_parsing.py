from pathlib import Path
from src.core.css_patcher import load_css_vars, load_css_selector_overrides, collect_css_from_dir


def test_load_css_vars_and_selectors_from_file(tmp_path: Path):
    css = tmp_path / "theme.css"
    css.write_text(
        ".green { color: #00FF00; }\n:root { --primary: #112233; --accent: #AABBCCDD; }\n",
        encoding="utf-8",
    )

    vars_ = load_css_vars(css)
    sel = load_css_selector_overrides(css)

    assert vars_["--primary"] == "#112233"
    assert vars_["--accent"] == "#AABBCCDD"
    assert (".green", "color") in sel
    assert ("green", "color") in sel
    assert sel[(".green", "color")] == "#00FF00"


def test_collect_css_from_dir_scans_skin_and_colours(tmp_path: Path):
    skin = tmp_path / "skins" / "my"
    (skin / "colours").mkdir(parents=True)
    # skin root file
    (skin /
     "root.uss").write_text(":root{--root:#010203;}\n", encoding="utf-8")
    # colours file
    (skin / "colours" /
     "base.css").write_text(".green{color:#00FF00;}\n", encoding="utf-8")
    # config.json to mark as skin folder
    (skin / "config.json").write_text(
        "{""schema_version"":1,""name"":""MySkin"",""target_bundle"":""fm_base.bundle"",""output_bundle"":""fm_base.bundle"",""overrides"":{}}",
        encoding="utf-8",
    )

    vars_, sel = collect_css_from_dir(skin)
    assert vars_["--root"] == "#010203"
    assert (".green", "color") in sel
    assert sel[("green", "color")] == "#00FF00"
