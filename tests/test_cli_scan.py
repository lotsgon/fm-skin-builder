from types import SimpleNamespace
import json
import sys


def make_fake_env_for_scan():
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
        def __init__(self, name, data):
            self.type = FakeObjType("MonoBehaviour")
            self._data = data
            self.path_id = 42

        def read(self):
            return self._data

    class FakeFile:
        def save(self):
            return b"bundle-bytes"

    class FakeEnv:
        def __init__(self, objects):
            self.objects = objects
            self.file = FakeFile()

    colors = [FakeColor(1.0, 0.0, 0.0, 1.0), FakeColor(0.0, 1.0, 0.0, 1.0)]
    strings = ["--primary", "--accent"]
    rules = [
        FakeRule([FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])]),
        FakeRule([FakeProperty("background-color",
                 [FakeValue(3, 1), FakeValue(4, 1)])])
    ]
    complex_selectors = [
        FakeComplexSelector(0, [FakeSelector([FakeSelPart("green", 3)])]),
        FakeComplexSelector(1, [FakeSelector([FakeSelPart("panel", 3)])]),
    ]
    data = FakeData("Style", strings, colors, rules, complex_selectors)
    return FakeEnv([FakeObj("Style", data)])


def test_cli_scan_exports_index_and_uss(tmp_path, monkeypatch):
    # Prepare bundle file
    bundle = tmp_path / "ui.bundle"
    bundle.write_bytes(b"orig")

    # Mock UnityPy
    from fm_skin_builder.core import bundle_inspector as inspector
    inspector.UnityPy = SimpleNamespace(
        load=lambda path: make_fake_env_for_scan())

    # Run CLI
    out_dir = tmp_path / "scan_out"
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "scan", "--bundle",
            str(bundle), "--out", str(out_dir), "--export-uss"]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Assert index written
    bundle_out = out_dir / bundle.stem
    index_file = bundle_out / "bundle_index.json"
    assert index_file.exists()
    data = json.loads(index_file.read_text(encoding="utf-8"))
    # var map contains our two vars
    assert "--primary" in data["var_map"]
    assert "--accent" in data["var_map"]
    # selector map contains our selectors
    assert ".green" in data["selector_map"] or "green" in data["selector_map"]
    assert ".panel" in data["selector_map"] or "panel" in data["selector_map"]
    # uss exported
    uss_dir = bundle_out / "scan_uss"
    assert any(p.suffix == ".uss" for p in uss_dir.iterdir())
