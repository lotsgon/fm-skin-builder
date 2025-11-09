import json
from types import SimpleNamespace

from fm_skin_builder.core.css_patcher import run_patch


class FakeTexture2DData:
    def __init__(self, name: str):
        self.m_Name = name
        self.saved = False
        self.m_Width = 100
        self.m_Height = 50

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


def test_texture_mapping_json_alias_with_spaces(tmp_path, caplog):
    # Skin config and mapping
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "backgrounds").mkdir(parents=True)
    (skin / "assets").mkdir(parents=True, exist_ok=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/backgrounds"]
    }), encoding="utf-8")
    # mapping: target (Sky Bet League One) -> source (my_background)
    (skin / "assets" / "mapping.json").write_text(json.dumps({
        "Sky Bet League One": "my_background"
    }), encoding="utf-8")

    # Replacement file using custom name
    (skin / "assets" / "backgrounds" / "my_background.jpg").write_bytes(b"JPEGDATA")

    # Bundle and env: Texture2D aliased via AssetBundle container name with spaces
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    tex_data = FakeTexture2DData("internal_tex")
    tex_obj = FakeObj("Texture2D", tex_data, path_id=3003)

    # AssetBundle container contains human-friendly name with spaces
    container_entry = SimpleNamespace(
        first="Sky Bet League One.png", second=SimpleNamespace(m_PathID=3003))
    ab_data = SimpleNamespace(m_Container=[container_entry])
    ab_obj = FakeObj("AssetBundle", ab_data)

    env = FakeEnv([tex_obj, ab_obj])

    from fm_skin_builder.core import css_patcher as cp
    from fm_skin_builder.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    caplog.set_level("INFO")
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    assert tex_data.saved is True
    assert (out_dir / "ui.bundle").exists()
