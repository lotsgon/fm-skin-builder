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


def test_texture_swap_via_assetbundle_container_alias(tmp_path, monkeypatch, caplog):
    # Skin with config v2 and includes backgrounds
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "backgrounds").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/backgrounds"]
    }), encoding="utf-8")

    # Replacement file uses the container alias name, different format
    (skin / "assets" / "backgrounds" /
     "premier_league_skin_fm26.jpg").write_bytes(b"JPGDATA")

    # Bundle at repo root for inference
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # Texture2D has a different m_Name than the container alias
    tex_data = FakeTexture2DData("pl_skin_internal")
    tex_obj = FakeObj("Texture2D", tex_data, path_id=1001)

    # AssetBundle container maps alias name to texture path id
    container_entry = SimpleNamespace(
        first="premier_league_skin_fm26.png", second=SimpleNamespace(m_PathID=1001))
    ab_data = SimpleNamespace(m_Container=[container_entry])
    ab_obj = FakeObj("AssetBundle", ab_data)

    env = FakeEnv([tex_obj, ab_obj])

    # Wire env loader
    from src.core import css_patcher as cp
    from src.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    caplog.set_level("INFO")
    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    # Texture should be saved
    assert tex_data.saved is True
    # And a modified bundle written
    assert any(p.name.endswith("_modified.bundle") for p in out_dir.iterdir())
    # Cross-format warning should be present
    assert any("Format mismatch" in rec.message for rec in caplog.records)
