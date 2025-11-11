"""
Tests for font replacement functionality.
"""

from types import SimpleNamespace
import json
import pytest

from fm_skin_builder.core.css_patcher import run_patch


class FakeFontData:
    """Mock Unity Font object."""

    def __init__(self, name: str):
        self.m_Name = name
        self.m_FontData = b"original-font-data"
        self.saved = False

    def save(self):
        self.saved = True


class FakeObjType:
    """Mock Unity object type."""

    def __init__(self, name):
        self.name = name


class FakeObj:
    """Mock Unity object."""

    def __init__(self, data, obj_type="Font"):
        self.type = FakeObjType(obj_type)
        self._data = data

    def read(self):
        return self._data

    def save_typetree(self, data):
        """Mock save_typetree method."""
        self._data = data
        data.save()


class FakeFile:
    """Mock Unity bundle file."""

    def save(self):
        return b"bundle-bytes"


class FakeEnv:
    """Mock UnityPy environment."""

    def __init__(self, objects):
        self.objects = objects
        self.file = FakeFile()


def test_font_swap_with_includes(tmp_path, monkeypatch):
    """Test that fonts are replaced when included in config."""
    # Create skin with config and font files
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps(
            {"schema_version": 2, "name": "Demo", "includes": ["fonts"]}
        ),
        encoding="utf-8",
    )

    # Create replacement font file
    test_font_data = b"TTF-REPLACEMENT-DATA"
    (skin / "assets" / "fonts" / "DINPro-Medium.ttf").write_bytes(test_font_data)

    # Create bundle file
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake Unity environment with a Font object
    data_font = FakeFontData("DINPro-Medium")
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify font was replaced
    assert data_font.saved is True
    assert data_font.m_FontData == test_font_data
    assert result.font_replacements_total == 1
    assert result.font_bundles_written == 1
    assert (out_dir / "fonts.bundle").exists()


def test_font_swap_with_assets_fonts_include(tmp_path, monkeypatch):
    """Test that fonts are replaced with 'assets/fonts' in includes."""
    # Create skin with config
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps(
            {"schema_version": 2, "name": "Demo", "includes": ["assets/fonts"]}
        ),
        encoding="utf-8",
    )

    # Create replacement font
    test_font_data = b"OTF-REPLACEMENT-DATA"
    (skin / "assets" / "fonts" / "Roboto-Regular.otf").write_bytes(test_font_data)

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment
    data_font = FakeFontData("Roboto-Regular")
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify
    assert data_font.saved is True
    assert data_font.m_FontData == test_font_data
    assert result.font_replacements_total == 1


def test_font_swap_with_all_include(tmp_path, monkeypatch):
    """Test that fonts are replaced with 'all' in includes."""
    # Create skin with 'all' in includes
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "Demo", "includes": ["all"]}),
        encoding="utf-8",
    )

    # Create replacement font
    test_font_data = b"TTF-DATA"
    (skin / "assets" / "fonts" / "TestFont.ttf").write_bytes(test_font_data)

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment
    data_font = FakeFontData("TestFont")
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify
    assert data_font.saved is True
    assert result.font_replacements_total == 1


def test_font_swap_no_fonts_without_include(tmp_path, monkeypatch):
    """Test that fonts are NOT replaced when not in includes."""
    # Create skin WITHOUT font includes
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps(
            {"schema_version": 2, "name": "Demo", "includes": ["assets/icons"]}
        ),
        encoding="utf-8",
    )

    # Create font file (should be ignored)
    (skin / "assets" / "fonts" / "TestFont.ttf").write_bytes(b"TTF-DATA")

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment
    data_font = FakeFontData("TestFont")
    original_data = data_font.m_FontData
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify font was NOT replaced
    assert data_font.m_FontData == original_data
    assert result.font_replacements_total == 0


def test_font_swap_dry_run(tmp_path, monkeypatch):
    """Test that dry-run doesn't actually replace fonts."""
    # Create skin
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "Demo", "includes": ["fonts"]}),
        encoding="utf-8",
    )

    # Create font
    (skin / "assets" / "fonts" / "TestFont.ttf").write_bytes(b"NEW-DATA")

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment
    data_font = FakeFontData("TestFont")
    original_data = data_font.m_FontData
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch with dry_run=True
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=True)

    # Verify font was NOT actually modified
    assert data_font.m_FontData == original_data
    assert data_font.saved is False
    # But dry-run should report it would replace
    assert result.font_replacements_total == 1
    # No bundles actually written
    assert result.font_bundles_written == 0
    assert not (out_dir / "fonts.bundle").exists()


def test_font_swap_with_mapping_file(tmp_path, monkeypatch):
    """Test explicit font mapping via font-mapping.json."""
    # Create skin
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "Demo", "includes": ["fonts"]}),
        encoding="utf-8",
    )

    # Create font mapping file
    (skin / "assets" / "fonts" / "font-mapping.json").write_text(
        json.dumps({"DINPro-Medium": "CustomFont.ttf"}), encoding="utf-8"
    )

    # Create font with custom name
    test_font_data = b"CUSTOM-FONT-DATA"
    (skin / "assets" / "fonts" / "CustomFont.ttf").write_bytes(test_font_data)

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment with DINPro-Medium font
    data_font = FakeFontData("DINPro-Medium")
    env = FakeEnv([FakeObj(data_font, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify font was replaced with mapped file
    assert data_font.saved is True
    assert data_font.m_FontData == test_font_data
    assert result.font_replacements_total == 1


def test_font_swap_skips_non_font_objects(tmp_path, monkeypatch):
    """Test that non-Font objects are ignored."""
    # Create skin
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "Demo", "includes": ["fonts"]}),
        encoding="utf-8",
    )

    # Create font
    (skin / "assets" / "fonts" / "TestFont.ttf").write_bytes(b"NEW-DATA")

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment with mixed object types
    data_font = FakeFontData("TestFont")
    data_texture = FakeFontData("SomeTexture")  # Not a Font type
    env = FakeEnv([FakeObj(data_font, "Font"), FakeObj(data_texture, "Texture2D")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify only Font was processed
    assert data_font.saved is True
    assert data_texture.saved is False  # Should not be touched
    assert result.font_replacements_total == 1


def test_font_swap_multiple_fonts(tmp_path, monkeypatch):
    """Test replacing multiple fonts in one bundle."""
    # Create skin
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "fonts").mkdir(parents=True)
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "Demo", "includes": ["fonts"]}),
        encoding="utf-8",
    )

    # Create multiple font files
    font1_data = b"FONT1-DATA"
    font2_data = b"FONT2-DATA"
    (skin / "assets" / "fonts" / "Font1.ttf").write_bytes(font1_data)
    (skin / "assets" / "fonts" / "Font2.otf").write_bytes(font2_data)

    # Create bundle
    bundle_file = tmp_path / "fonts.bundle"
    bundle_file.write_bytes(b"orig")

    # Create fake environment with multiple fonts
    data_font1 = FakeFontData("Font1")
    data_font2 = FakeFontData("Font2")
    env = FakeEnv([FakeObj(data_font1, "Font"), FakeObj(data_font2, "Font")])

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp

    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Run patch
    out_dir = tmp_path / "out"
    result = run_patch(skin, out_dir, bundle=bundle_file, dry_run=False)

    # Verify both fonts were replaced
    assert data_font1.saved is True
    assert data_font1.m_FontData == font1_data
    assert data_font2.saved is True
    assert data_font2.m_FontData == font2_data
    assert result.font_replacements_total == 2
