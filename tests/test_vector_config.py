from fm_skin_builder.core.textures import _coerce_vector_color, _normalise_vector_config


def test_coerce_vector_color_hex_string():
    result = _coerce_vector_color("#FF8844")
    assert result == (255, 136, 68, 255)


def test_coerce_vector_color_float_list():
    result = _coerce_vector_color([1.0, 0.5, 0.0, 0.25])
    assert result == (255, 128, 0, 64)


def test_normalise_vector_config_svg_file(tmp_path):
    skin_root = tmp_path
    assets_dir = skin_root / "assets" / "icons"
    assets_dir.mkdir(parents=True)
    svg_path = assets_dir / "ability_minimum.svg"
    svg_path.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg'><path d='M0 0 L10 0 L0 10 z'/></svg>",
        encoding="utf-8",
    )

    config = {
        "type": "vector",
        "svg_file": "assets/icons/ability_minimum.svg",
        "color": "#ff000080",
        "scale": 0.5,
    }

    normalised = _normalise_vector_config(config, skin_root)
    assert normalised is not None
    assert normalised.get("shape") == "custom"
    assert "svg_path" in normalised
    assert "M0 0" in normalised["svg_path"]
    assert normalised.get("__svg_file_path") == str(svg_path)
    assert normalised.get("color") == (255, 0, 0, 128)
    assert normalised.get("scale") == 0.5


def test_normalise_vector_config_missing_svg_returns_none(tmp_path):
    config = {
        "type": "vector",
        "svg_file": "assets/icons/missing.svg",
    }
    normalised = _normalise_vector_config(config, tmp_path)
    assert normalised is None


def test_normalise_vector_config_relative_to_map_dir(tmp_path):
    skin_root = tmp_path
    map_dir = skin_root / "assets" / "icons"
    map_dir.mkdir(parents=True)
    svg_file = map_dir / "min-none.svg"
    svg_file.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg'><path d='M0 0 L0 1 L1 0 z'/></svg>",
        encoding="utf-8",
    )

    config = {
        "type": "vector",
        "svg_file": "min-none.svg",
        "__map_dir": str(map_dir),
    }

    normalised = _normalise_vector_config(config, skin_root)
    assert normalised is not None
    assert "svg_path" in normalised
    assert "M0 0" in normalised["svg_path"]


def test_read_svg_circle(tmp_path):
    svg_file = tmp_path / "circle.svg"
    svg_file.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg'><circle cx='10' cy='5' r='3' /></svg>",
        encoding="utf-8",
    )
    config = {
        "type": "vector",
        "svg_file": str(svg_file),
    }
    normalised = _normalise_vector_config(config, tmp_path)
    assert normalised is not None
    svg_path = normalised.get("svg_path")
    assert svg_path and "A" in svg_path
