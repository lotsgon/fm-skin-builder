import json
from types import SimpleNamespace

from fm_skin_builder.core.css_patcher import run_patch


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


def test_sprite_atlas_replacement_blocked(tmp_path, caplog):
    # Skin opts into icons
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "icons").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/icons"]
    }), encoding="utf-8")

    # Provide a replacement mapped to a sprite name
    (skin / "assets" / "icons" / "my_icon.png").write_bytes(b"PNGDATA")
    (skin / "assets" / "icons" / "mapping.json").write_text(json.dumps({
        "my_icon": "AtlasSpriteA"
    }), encoding="utf-8")

    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # One Texture2D used by two different Sprite aliases (atlas-like)
    tex = FakeTexture2DData("atlasTex")
    tex_obj = FakeObj("Texture2D", tex, path_id=9009)

    sprite_a = SimpleNamespace(m_Name="AtlasSpriteA", m_RD=SimpleNamespace(
        texture=SimpleNamespace(m_PathID=9009)))
    sprite_b = SimpleNamespace(m_Name="AtlasSpriteB", m_RD=SimpleNamespace(
        texture=SimpleNamespace(m_PathID=9009)))
    sprite_obj_a = FakeObj("Sprite", sprite_a)
    sprite_obj_b = FakeObj("Sprite", sprite_b)

    env = FakeEnv([tex_obj, sprite_obj_a, sprite_obj_b])

    from fm_skin_builder.core import css_patcher as cp
    from fm_skin_builder.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    caplog.set_level("INFO")
    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    # Should be blocked: texture unchanged, no output file, log error
    assert tex.saved is False
    assert not any(p.suffix == ".bundle" for p in out_dir.iterdir())
    assert any(
        "Atlas replacement is not supported" in rec.message for rec in caplog.records)
