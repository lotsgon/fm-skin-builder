from types import SimpleNamespace
import json

from fm_skin_builder.core.css_patcher import run_patch


class FakeTexture2DData:
    def __init__(self, name: str):
        self.m_Name = name
        self._replaced_bytes = None
        self.saved = False

    def save(self):
        self.saved = True


class FakeObjType:
    def __init__(self, name):
        self.name = name


class FakeObj:
    def __init__(self, data):
        self.type = FakeObjType("Texture2D")
        self._data = data

    def read(self):
        return self._data


class FakeFile:
    def save(self):
        return b"bundle-bytes"


class FakeEnv:
    def __init__(self, objects):
        self.objects = objects
        self.file = FakeFile()


def test_texture_swap_icons_with_includes(tmp_path, monkeypatch):
    # Skin with config v2 and includes assets/icons
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "icons").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/icons"]
    }), encoding="utf-8")
    # Provide replacement image bytes
    (skin / "assets" / "icons" / "Logo.png").write_bytes(b"PNGDATA")

    # Bundle at repo root for inference
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # Fake UnityPy env with a Texture2D named Logo
    data_logo = FakeTexture2DData("Logo")
    env = FakeEnv([FakeObj(data_logo)])
    from fm_skin_builder.core import css_patcher as cp
    from fm_skin_builder.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    run_patch(skin, out_dir, bundle=None, dry_run=False)

    # Ensure texture was replaced/saved and output bundle exists
    assert data_logo.saved is True
    assert (out_dir / "ui.bundle").exists()
