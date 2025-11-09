import json
from types import SimpleNamespace
import pytest

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


@pytest.mark.parametrize("provided", ["base-only", "all-variants"])
def test_texture_variant_awareness(tmp_path, monkeypatch, caplog, provided):
    # Skin with includes assets/icons
    skin = tmp_path / "skins" / "demo"
    (skin / "assets" / "icons").mkdir(parents=True)
    (skin / "config.json").write_text(json.dumps({
        "schema_version": 2,
        "name": "Demo",
        "includes": ["assets/icons"]
    }), encoding="utf-8")

    # Provide replacement image bytes
    (skin / "assets" / "icons" / "Logo.png").write_bytes(b"P0")
    if provided == "all-variants":
        (skin / "assets" / "icons" / "Logo_x2.png").write_bytes(b"P2")
        (skin / "assets" / "icons" / "Logo_x4.png").write_bytes(b"P4")

    # Bundle at repo root for inference
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")

    # Fake UnityPy env with texture variants: 1x,2x,4x
    data1 = FakeTexture2DData("Logo")
    data2 = FakeTexture2DData("Logo_x2")
    data4 = FakeTexture2DData("Logo_x4")
    env = FakeEnv([FakeObj(data1), FakeObj(data2), FakeObj(data4)])

    # Wire both modules to same env
    from fm_skin_builder.core import css_patcher as cp
    from fm_skin_builder.core import textures as tx
    cp.UnityPy = SimpleNamespace(load=lambda path: env)
    tx.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    if provided == "base-only":
        caplog.set_level("WARNING")
        run_patch(skin, out_dir, bundle=None, dry_run=False)
        # Only base variant should be saved; others untouched
        assert data1.saved is True
        assert data2.saved is False
        assert data4.saved is False
        assert any(
            "Only 1/3 variants provided" in rec.message for rec in caplog.records)
    else:
        run_patch(skin, out_dir, bundle=None, dry_run=False)
        assert data1.saved is True
        assert data2.saved is True
        assert data4.saved is True
