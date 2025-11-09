from pathlib import Path
from types import SimpleNamespace


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

    def save(self):
        self._saved = True


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


def test_no_changes_no_outputs(tmp_path: Path):
    # A stylesheet with color black and var --primary mapped to same #000000
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rule = FakeRule(
        [FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])])
    data = FakeData("Style", strings, colors, [rule])
    env = FakeEnv([FakeObj(data)])

    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(load=lambda path: env)

    out_dir = tmp_path / "out"
    patcher = cp.CssPatcher(css_vars={"--primary": "#000000"}, selector_overrides={
    }, patch_direct=False, debug_export_dir=out_dir / "debug_uss")
    patcher.patch_bundle_file(tmp_path / "ui.bundle", out_dir)

    # No out dir should be created as nothing changed
    assert not out_dir.exists()
