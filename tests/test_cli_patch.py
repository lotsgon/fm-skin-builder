from types import SimpleNamespace
import json
import sys


def make_fake_env_with_simple_stylesheet():
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

    # Construct a stylesheet with var reference and color ref to same index 0
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rules = [
        FakeRule([FakeProperty("color", [FakeValue(3, 0), FakeValue(4, 0)])])]
    data = FakeData("Style", strings, colors, rules)
    env = FakeEnv([FakeObj(data)])
    return env


def test_cli_patch_patches_with_explicit_bundle_dir(tmp_path, monkeypatch):
    # Arrange skin folder
    skin = tmp_path / "skins" / "demo"
    (skin / "colours").mkdir(parents=True)
    bundle_file = tmp_path / "fm_base.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({
            "schema_version": 2,
            "name": "Demo"
        }),
        encoding="utf-8",
    )
    (skin / "colours" /
     "base.uss").write_text(":root{--primary:#112233;}\n", encoding="utf-8")

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(
        load=lambda path: make_fake_env_with_simple_stylesheet())

    # Act: call CLI main with argv (explicit --bundle dir)
    out_dir = tmp_path / "out"
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "patch", str(skin), "--out",
            str(out_dir), "--debug-export", "--bundle", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Assert outputs
    assert out_dir.exists()
    assert (out_dir / "fm_base.bundle").exists()
    debug_dir = out_dir / "debug_uss"
    assert debug_dir.exists()
    files = {p.name for p in debug_dir.iterdir()}
    assert any(n.startswith("original_") for n in files)
    assert any(n.startswith("patched_") for n in files)


def test_cli_patch_with_bundle_dir(tmp_path, monkeypatch):
    # Arrange css dir (not a skin)
    css_dir = tmp_path / "css"
    css_dir.mkdir()
    (css_dir /
     "t.uss").write_text(":root{--primary:#445566;}\n", encoding="utf-8")

    # Arrange bundle dir
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    (bundles / "ui.bundle").write_bytes(b"orig")

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(
        load=lambda path: make_fake_env_with_simple_stylesheet())

    # Act: call CLI main with argv specifying --bundle dir
    out_dir = tmp_path / "out2"
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "patch", str(css_dir), "--out",
            str(out_dir), "--bundle", str(bundles)]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Assert
    assert out_dir.exists()
    assert (out_dir / "ui.bundle").exists()


def test_cli_patch_requires_bundle_when_not_inferable(tmp_path, monkeypatch):
    # Arrange a CSS dir without config.json
    css_dir = tmp_path / "css"
    css_dir.mkdir()
    (css_dir /
     "t.css").write_text(":root{--primary:#778899;}\n", encoding="utf-8")

    # Mock UnityPy (shouldn't be used)
    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(load=lambda path: None)

    # Act: call CLI without --bundle; expect early return, no out dir created
    out_dir = tmp_path / "out3"
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "patch", str(css_dir), "--out", str(out_dir)]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Assert
    assert not out_dir.exists()


def test_cli_patch_dry_run_produces_no_outputs(tmp_path, monkeypatch):
    # Arrange skin folder
    skin = tmp_path / "skins" / "demo"
    (skin / "colours").mkdir(parents=True)
    bundle_file = tmp_path / "fm_base.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({
            "schema_version": 2,
            "name": "Demo"
        }),
        encoding="utf-8",
    )
    (skin / "colours" /
     "base.uss").write_text(":root{--primary:#112233;}\n", encoding="utf-8")

    # Mock UnityPy
    from fm_skin_builder.core import css_patcher as cp
    cp.UnityPy = SimpleNamespace(
        load=lambda path: make_fake_env_with_simple_stylesheet())

    # Act: call CLI main with argv including --dry-run and --debug-export (which should be ignored)
    out_dir = tmp_path / "out_dry"
    from fm_skin_builder.cli import main as cli_main
    argv = ["prog", "patch", str(skin), "--out",
            str(out_dir), "--debug-export", "--dry-run"]
    monkeypatch.setattr(sys, "argv", argv, raising=False)
    cli_main.main()

    # Assert: no outputs should be created in dry-run
    if out_dir.exists():
        # directory should be empty (no modified bundles, no debug)
        entries = list(out_dir.iterdir())
        assert not entries, f"Dry-run should not produce files, found: {[e.name for e in entries]}"
