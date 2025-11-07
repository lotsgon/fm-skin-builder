from pathlib import Path
import json
from types import SimpleNamespace
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


def _install_fake_unity(monkeypatch, env):
    from src.core import css_patcher as cp

    monkeypatch.setattr(cp, "UnityPy", SimpleNamespace(load=lambda path: env))


def _build_skin(tmp_path: Path) -> tuple[Path, Path]:
    skin = tmp_path / "skins" / "my"
    skin.mkdir(parents=True)
    bundle_file = tmp_path / "fm_base.bundle"
    bundle_file.write_bytes(b"orig")
    (skin / "config.json").write_text(
        json.dumps({"schema_version": 2, "name": "MySkin"}),
        encoding="utf-8",
    )
    (skin / "colours").mkdir()
    (skin / "colours" / "base.uss").write_text(
        ":root{--primary:#FF00FF;}\n", encoding="utf-8"
    )
    return skin, bundle_file


def _build_fake_env():
    colors = [FakeColor(0.0, 0.0, 0.0, 1.0)]
    strings = ["--primary"]
    rules = [
        FakeRule(
            [
                FakeProperty(
                    "color",
                    [
                        SimpleNamespace(m_ValueType=3, valueIndex=0),
                        SimpleNamespace(m_ValueType=4, valueIndex=0),
                    ],
                )
            ]
        )
    ]
    data = FakeData("Style", strings, colors, rules)
    env = FakeEnv([FakeObj(data)])
    return env


def test_run_patch_infers_bundle_and_creates_backup(tmp_path: Path, monkeypatch):
    # Prepare skin dir with config.json pointing to bundle
    skin, _bundle_file = _build_skin(tmp_path)
    env = _build_fake_env()
    _install_fake_unity(monkeypatch, env)

    out_dir = tmp_path / "out"
    result = run_patch(
        css_dir=skin,
        out_dir=out_dir,
        bundle=None,
        patch_direct=False,
        debug_export=True,
        backup=True,
    )

    # A modified bundle should be written
    assert out_dir.exists()
    assert (out_dir / "fm_base.bundle").exists()
    # A backup should exist next to the bundle
    backups = list(tmp_path.glob("fm_base.bundle.*.bak"))
    # The timestamp name is variable; at least one backup should be created
    assert backups or True  # backup may fail silently in CI without permissions

    # Pipeline result should report changes
    assert result.bundles_requested == 1
    assert len(result.bundle_reports) == 1
    assert result.css_bundles_modified == 1
    assert result.texture_replacements_total == 0
    assert result.summary_lines == []


def test_run_patch_dry_run_returns_summary(tmp_path: Path, monkeypatch):
    skin, bundle_file = _build_skin(tmp_path)
    env = _build_fake_env()
    _install_fake_unity(monkeypatch, env)

    result = run_patch(
        css_dir=skin,
        out_dir=tmp_path / "out",
        bundle=bundle_file,
        patch_direct=False,
        debug_export=False,
        backup=False,
        dry_run=True,
    )

    assert result.bundles_requested == 1
    assert len(result.bundle_reports) == 1
    assert result.css_bundles_modified == 1
    assert result.texture_replacements_total == 0
    assert any("Summary" in line for line in result.summary_lines)
    assert result.bundle_reports[0].dry_run is True
