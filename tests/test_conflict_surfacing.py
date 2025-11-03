from pathlib import Path
from types import SimpleNamespace
import json

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


class FakeSelPart:
    def __init__(self, val, typ):
        self.m_Value = val
        self.m_Type = typ


class FakeSelector:
    def __init__(self, parts):
        self.m_Parts = parts


class FakeComplexSelector:
    def __init__(self, idx, selectors):
        self.ruleIndex = idx
        self.m_Selectors = selectors


class FakeData:
    def __init__(self, name, strings, colors, rules, complex_selectors):
        self.m_Name = name
        self.strings = strings
        self.colors = colors
        self.m_Rules = rules
        self.m_ComplexSelectors = complex_selectors

    def save(self):
        pass


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


def test_conflict_surfacing_logs_multi_asset_touch(tmp_path: Path, monkeypatch, caplog):
    # Arrange skin with config and CSS override for .green color
    skin = tmp_path / "skins" / "conflict"
    (skin / "colours").mkdir(parents=True)
    bundle_file = tmp_path / "ui.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({
            "schema_version": 1,
            "name": "Conflict",
            "target_bundle": str(bundle_file),
            "output_bundle": "ui.bundle",
            "overrides": {},
        }),
        encoding="utf-8",
    )
    # Use fallback synthetic selector .rule-0 to avoid relying on complex selector wiring in tests
    (skin / "colours" / "override.uss").write_text(".rule-0{color:#112233;}\n", encoding="utf-8")

    # Build two assets with one rule each; without complex selectors, patcher uses fallback .rule-0 selector
    strings = ["--x"]  # not used here
    colors1 = [FakeColor(1.0, 0.0, 0.0, 1.0)]
    colors2 = [FakeColor(0.0, 1.0, 0.0, 1.0)]
    ruleA = FakeRule([FakeProperty("color", [FakeValue(4, 0)])])
    ruleB = FakeRule([FakeProperty("color", [FakeValue(4, 0)])])
    dataA = FakeData("StyleA", strings, colors1, [ruleA], [])
    dataB = FakeData("StyleB", strings, colors2, [ruleB], [])

    from src.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(load=lambda path: FakeEnv([FakeObj(dataA), FakeObj(dataB)]))

    caplog.set_level("INFO")
    out_dir = tmp_path / "out"
    # Dry run to avoid filesystem writes and capture summary logs
    run_patch(css_dir=skin, out_dir=out_dir, bundle=None, dry_run=True)

    logs = "\n".join([r.message for r in caplog.records])
    assert "Selector overrides affecting multiple assets" in logs
    # We normalize selector to have a leading dot
    assert ".rule-0 / color" in logs
