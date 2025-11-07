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


def test_texture_mapping_in_backgrounds_folder(tmp_path):
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "backgrounds").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/backgrounds"]
    }), encoding="utf-8")

    # mapping in subfolder backgrounds
    (skin / "assets" / "backgrounds" / "mapping.json").write_text(json.dumps({
        "Sky Bet League One": "background_1"
    }), encoding="utf-8")
    # replacement file uses the custom name
    (skin / "assets" / "backgrounds" / "background_1.jpg").write_bytes(b"JPGDATA")

    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # Texture aliased via AssetBundle container
    tex_data = FakeTexture2DData("internal_tex")
    tex_obj = FakeObj("Texture2D", tex_data, path_id=5005)

    container_entry = SimpleNamespace(
        first="Sky Bet League One.png", second=SimpleNamespace(m_PathID=5005))
    ab_data = SimpleNamespace(m_Container=[container_entry])
    ab_obj = FakeObj("AssetBundle", ab_data)

    env = FakeEnv([tex_obj, ab_obj])

    from src.core import css_patcher as cp
    from src.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    assert tex_data.saved is True
    assert (out_dir / "ui.bundle").exists()
