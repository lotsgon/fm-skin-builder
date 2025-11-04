import json
from types import SimpleNamespace

from src.core.css_patcher import run_patch


class FakeTexture2DData:
    def __init__(self, name: str):
        self.m_Name = name
        self.saved = False

    def save(self):
        self.saved = True


class FakeObjType:
    def __init__(self, name):
        self.name = name


class FakeObj:
    def __init__(self, type_name, data, path_id=None):
        self.type = FakeObjType(type_name)
        self._data = data
        if path_id is not None:
            self.path_id = path_id

    def read(self):
        return self._data


class FakeFile:
    def save(self):
        return b"bundle-bytes"


class FakeEnv:
    def __init__(self, objects):
        self.objects = objects
        self.file = FakeFile()


def test_texture_swap_via_sprite_alias(tmp_path, monkeypatch):
    # Skin config with icons includes
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "icons").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/icons"]
    }), encoding="utf-8")

    # Replacement file uses Sprite name
    (skin / "assets" / "icons" / "HeroBg.png").write_bytes(b"PNGDATA")

    # Bundle at repo root for inference
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # Texture2D object
    tex_data = FakeTexture2DData("internal_tex")
    tex_obj = FakeObj("Texture2D", tex_data, path_id=2002)

    # Sprite referencing the texture via m_RD.texture.m_PathID
    sprite_rd = SimpleNamespace(texture=SimpleNamespace(m_PathID=2002))
    sprite_data = SimpleNamespace(m_Name="HeroBg", m_RD=sprite_rd)
    sprite_obj = FakeObj("Sprite", sprite_data)

    env = FakeEnv([tex_obj, sprite_obj])

    # Wire env loader
    from src.core import css_patcher as cp
    from src.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    # Texture should be saved through the alias mapping
    assert tex_data.saved is True
    # And modified bundle exists
    assert any(p.name.endswith("_modified.bundle") for p in out_dir.iterdir())
