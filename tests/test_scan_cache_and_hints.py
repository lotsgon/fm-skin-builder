from pathlib import Path
from types import SimpleNamespace
import json
import pytest

from src.core.css_patcher import run_patch


class FakeColor:
    def __init__(self, r=0.0, g=0.0, b=0.0, a=1.0):
        self.r, self.g, self.b, self.a = r, g, b, a


class FakeValue:
    def __init__(self, t, idx):
        self.m_ValueType = t
        self.valueIndex = idx


class FakeProperty:
    def __init__(self, name, values):
        self.m_Name = name
        self.m_Values = values


class FakeRule:
    def __init__(self, props):
        self.m_Properties = props


class FakeData:
    def __init__(self, name, strings, colors, rules):
        self.m_Name = name
        self.strings = strings
        self.colors = colors
        self.m_Rules = rules
        self.saved = False

    def save(self):
        self.saved = True


class FakeObjType:
    def __init__(self, name):
        self.name = name


class FakeObj:
    def __init__(self, data):
        self.type = FakeObjType("MonoBehaviour")
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


def make_env_two_assets():
    # Both assets reference var index 0 as both var (type 3) and color (type 4)
    strings = ["--primary"]
    colors_A = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    colors_B = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    rules = [FakeRule([FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])])]
    dataA = FakeData("StyleA", strings, colors_A, rules)
    dataB = FakeData("StyleB", strings, colors_B, rules)
    return FakeEnv([FakeObj(dataA), FakeObj(dataB)]), dataA, dataB


def test_scan_cache_prefilters_assets(tmp_path: Path, monkeypatch):
    # Arrange skin with config and css var
    skin = tmp_path / "skins" / "demo"
    (skin / "colours").mkdir(parents=True)
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({
            "schema_version": 1,
            "name": "Demo",
            "target_bundle": str(bundle_file),
            "output_bundle": "ui.bundle",
            "overrides": {},
        }),
        encoding="utf-8",
    )
    (skin / "colours" / "base.uss").write_text(":root{--primary:#112233;}\n", encoding="utf-8")

    # Fake UnityPy env with two assets that would both qualify normally
    from src.core import css_patcher as cp
    env, dataA, dataB = make_env_two_assets()
    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    # Mock _refresh_index to return an index that only includes StyleA for var --primary
    fake_index = {
        "var_map": {
            "--primary": [
                {"asset": "StyleA", "rule": 0, "prop": "color", "index": 0}
            ]
        },
        "selector_map": {},
        "assets": [
            {"name": "StyleA"},
            {"name": "StyleB"},
        ],
    }
    monkeypatch.setattr(cp, "_refresh_index", lambda cache_skin_dir, bundle: fake_index)

    out_dir = tmp_path / "out"
    run_patch(css_dir=skin, out_dir=out_dir, bundle=None,
              patch_direct=False, debug_export=False, backup=False,
              use_scan_cache=True, refresh_scan_cache=True)

    # Only StyleA should have been saved due to cache candidate filtering
    assert dataA.saved is True
    assert dataB.saved is False


def test_hints_asset_filter_limits_targets(tmp_path: Path, monkeypatch):
    # Arrange skin with config, css, and hints limiting to StyleB
    skin = tmp_path / "skins" / "demo2"
    (skin / "colours").mkdir(parents=True)
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({
            "schema_version": 1,
            "name": "Demo2",
            "target_bundle": str(bundle_file),
            "output_bundle": "ui.bundle",
            "overrides": {},
        }),
        encoding="utf-8",
    )
    (skin / "colours" / "base.uss").write_text(":root{--primary:#334455;}\n", encoding="utf-8")
    (skin / "hints.txt").write_text("asset: StyleB\n", encoding="utf-8")

    # Fake UnityPy env with two assets as before
    from src.core import css_patcher as cp
    env, dataA, dataB = make_env_two_assets()
    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out_hints"
    run_patch(css_dir=skin, out_dir=out_dir, bundle=None,
              patch_direct=False, debug_export=False, backup=False,
              use_scan_cache=False)

    # Only StyleB should have been saved due to hint asset filter
    assert dataA.saved is False
    assert dataB.saved is True
