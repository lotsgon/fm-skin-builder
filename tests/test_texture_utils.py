from pathlib import Path

from src.core.texture_utils import (
    collect_replacement_stems,
    gather_texture_names_from_index,
    load_texture_name_map,
    should_swap_textures,
)


def test_collect_replacement_stems_filters_extensions(tmp_path: Path):
    icons = tmp_path / "assets" / "icons"
    icons.mkdir(parents=True)
    (icons / "one.png").write_bytes(b"")
    (icons / "two.JPG").write_bytes(b"")
    (icons / "three.svg").write_bytes(b"")
    (icons / "ignore.txt").write_bytes(b"")

    stems = collect_replacement_stems(icons)

    assert sorted(stems) == ["one", "three", "two"]


def test_load_texture_name_map_reads_overrides(tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir(parents=True)
    (assets / "mapping.json").write_text('{"src": "dest"}', encoding="utf-8")
    icons = assets / "icons"
    icons.mkdir(parents=True)
    (icons / "map.json").write_text('{"icon": "IconTarget"}', encoding="utf-8")

    mapping = load_texture_name_map(tmp_path)

    assert mapping["src"] == "dest"
    assert mapping["icon"] == "IconTarget"


def test_gather_texture_names_from_index_handles_mixed_values():
    names = gather_texture_names_from_index(
        {
            "textures": ["Icon_A", 123],
            "aliases": ["icon_b"],
            "sprites": None,
        }
    )

    assert names == {"Icon_A", "123", "icon_b"}


def test_should_swap_textures_matches_targets_and_wildcards():
    names = {"PlayerIcon", "panel_background"}

    assert should_swap_textures(
        bundle_name="characters_icons.bundle",
        texture_names=names,
        target_names={"playericon"},
        replace_stems=set(),
        want_icons=False,
        want_backgrounds=False,
    )

    assert should_swap_textures(
        bundle_name="characters.bundle",
        texture_names=names,
        target_names={"panel*"},
        replace_stems=set(),
        want_icons=False,
        want_backgrounds=False,
    )


def test_should_swap_textures_falls_back_to_bundle_name():
    assert should_swap_textures(
        bundle_name="ui_icons.bundle",
        texture_names=set(),
        target_names=set(),
        replace_stems=set(),
        want_icons=True,
        want_backgrounds=False,
    )

    assert not should_swap_textures(
        bundle_name="ui_misc.bundle",
        texture_names=set(),
        target_names=set(),
        replace_stems=set(),
        want_icons=False,
        want_backgrounds=False,
    )
