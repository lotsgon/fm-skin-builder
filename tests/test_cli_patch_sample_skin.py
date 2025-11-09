from pathlib import Path
from types import SimpleNamespace
import shutil
import sys


def fake_unity_env():
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

    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rules = [
        FakeRule([FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])])]
    data = FakeData("Style", strings, colors, rules)
    return FakeEnv([FakeObj(data)])


def test_cli_patch_uses_sample_skin(tmp_path, monkeypatch):
    # Locate sample skin in repo
    repo_root = Path(__file__).resolve().parent.parent
    sample_skin = repo_root / "skins" / "test_skin"
    assert sample_skin.exists()

    # Copy sample skin to tmp workspace
    skin_copy = tmp_path / "skins" / "test_skin"
    shutil.copytree(sample_skin, skin_copy)
    bundle_file = tmp_path / "fm_base.bundle"
    bundle_file.write_bytes(b"orig")
    # Config v2 has no bundle fields; inference will find the single bundle at repo root

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(load=lambda path: fake_unity_env())

    # Run CLI
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "patch", str(skin_copy), "--debug-export"]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Verify outputs
    packages_dir = skin_copy / "packages"
    assert packages_dir.exists()
    assert (packages_dir / "fm_base.bundle").exists()
    debug_dir = packages_dir / "debug_uss"
    assert debug_dir.exists()
    files = {p.name for p in debug_dir.iterdir()}
    assert any(n.startswith("original_") for n in files)
    assert any(n.startswith("patched_") for n in files)
