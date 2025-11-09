import json
from types import SimpleNamespace

from fm_skin_builder.core.css_patcher import run_patch


class FakeTexture2DData:
    def __init__(self, name: str):
        self.m_Name = name
        self.saved = False
        self.m_Width = 16
        self.m_Height = 16

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


def test_texture_mapping_target_to_source_variant(tmp_path):
    # Skin config and mapping (target -> source form)
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "icons").mkdir(parents=True)
    (skin / "assets").mkdir(parents=True, exist_ok=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/icons"]
    }), encoding="utf-8")

    # mapping: settings-small_4x (target) -> crown (source)
    (skin / "assets" / "icons" / "mapping.json").write_text(json.dumps({
        "settings-small_4x": "crown"
    }), encoding="utf-8")

    # Replacement file providing the 4x variant of crown
    (skin / "assets" / "icons" / "crown_x4.png").write_bytes(b"PNGDATA")

    # Bundle and env: Texture2D aliased via AssetBundle container name with _4x suffix
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    tex_data = FakeTexture2DData("internal_tex")
    tex_obj = FakeObj("Texture2D", tex_data, path_id=7777)

    # AssetBundle container contains the friendly alias with variant suffix
    container_entry = SimpleNamespace(
        first="settings-small_4x.png", second=SimpleNamespace(m_PathID=7777))
    ab_data = SimpleNamespace(m_Container=[container_entry])
    ab_obj = FakeObj("AssetBundle", ab_data)

    env = FakeEnv([tex_obj, ab_obj])

    from fm_skin_builder.core import css_patcher as cp
    from fm_skin_builder.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    assert tex_data.saved is True
    assert (out_dir / "ui.bundle").exists()
