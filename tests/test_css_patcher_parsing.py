from pathlib import Path
from fm_skin_builder.core.css_utils import load_css_vars, load_css_selector_overrides
from fm_skin_builder.core.css_sources import collect_css_from_dir


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

    collected = collect_css_from_dir(skin)
    assert collected.global_vars["--root"] == "#010203"
    assert collected.global_selectors[(".green", "color")] == "#00FF00"
    assert collected.global_selectors[("green", "color")] == "#00FF00"


def test_selector_override_without_trailing_semicolon(tmp_path: Path):
    css = tmp_path / "theme2.css"
    css.write_text(
        ".foo { color: #123456 }\n.bar { color: #abcdef; }\n",
        encoding="utf-8",
    )

    sel = load_css_selector_overrides(css)

    assert sel[(".foo", "color")] == "#123456"
    assert sel[("foo", "color")] == "#123456"
    assert sel[(".bar", "color")] == "#ABCDEF"


def test_rgb_and_rgba_colours_are_normalised(tmp_path: Path):
    css = tmp_path / "theme_rgb.css"
    css.write_text(
        ":root { --bright: rgb(17,34,51); --transparent: rgba(255, 0, 128, 0.5); --percent: rgba(100%,0%,0%,25%); }\n"
        ".blue { color: rgba(0, 255, 0, 0.25); }\n"
        ".pink { color: rgb(255, 100, 200); }\n",
        encoding="utf-8",
    )

    vars_ = load_css_vars(css)
    selectors = load_css_selector_overrides(css)

    assert vars_["--bright"] == "#112233"
    assert vars_["--transparent"] == "#FF008080"
    assert vars_["--percent"] == "#FF000040"
    assert selectors[(".blue", "color")] == "#00FF0040"
    assert selectors[(".pink", "color")] == "#FF64C8"
