from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Set

import pytest

from src.core.css_patcher import PipelineOptions, SkinPatchPipeline
from src.core.context import PatchReport


class FakeBundleContext:
    def __init__(self, bundle_path: Path, **_: object) -> None:
        self.bundle_path = bundle_path
        self._dirty = False
        self.env = SimpleNamespace(file=SimpleNamespace(save=lambda: b""))

    def __enter__(self) -> "FakeBundleContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def load(self) -> None:  # pragma: no cover - nothing to do for fake
        return None

    def mark_dirty(self) -> None:
        self._dirty = True

    def save_modified(
        self,
        out_dir: Path,
        *,
        dry_run: bool = False,
        suffix: str = "",
    ) -> Optional[Path]:
        if dry_run or not self._dirty:
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / \
            f"{self.bundle_path.stem}{suffix}{self.bundle_path.suffix}"
        out_path.write_bytes(b"patched")
        return out_path


class FakeCssService:
    def __init__(self, *_: object, **__: object) -> None:
        self._dry_run = False

    def apply(
        self,
        bundle_ctx: FakeBundleContext,
        *,
        candidate_assets: Optional[Set[str]] = None,
    ) -> PatchReport:
        report = PatchReport(bundle_ctx.bundle_path, dry_run=self._dry_run)
        report.assets_modified.add("FakeAsset")
        report.summary_lines.append(
            f"Dry run summary for {bundle_ctx.bundle_path.name}" if report.dry_run else "Patched bundle"
        )
        bundle_ctx.mark_dirty()
        return report


class RecordingTextureSwapService:
    calls: list[Path] = []

    def __init__(self, options) -> None:
        self.options = options

    def apply(self, bundle_ctx, skin_dir, out_dir, report):
        type(self).calls.append(bundle_ctx.bundle_path)
        report.texture_replacements += 1
        bundle_ctx.mark_dirty()
        return SimpleNamespace(replaced_count=1, out_path=None)


@pytest.fixture(autouse=True)
def reset_texture_service_calls():
    RecordingTextureSwapService.calls = []
    yield
    RecordingTextureSwapService.calls = []


def _setup_common_stubs(monkeypatch, *, dry_run: bool) -> None:
    monkeypatch.setattr(
        "src.core.css_patcher.BundleContext", FakeBundleContext)
    css_service = FakeCssService()
    css_service._dry_run = dry_run
    monkeypatch.setattr("src.core.css_patcher.CssPatchService",
                        lambda *a, **k: css_service)
    monkeypatch.setattr(
        "src.core.css_patcher.collect_css_from_dir",
        lambda path: ({"--primary": "#FFF"}, {(".selector", "color"): "#000"}),
    )
    monkeypatch.setattr(
        "src.core.css_patcher.load_targeting_hints",
        lambda path: (None, None, None),
    )
    monkeypatch.setattr(
        "src.core.css_patcher.collect_replacement_stems", lambda *a, **k: [])
    monkeypatch.setattr(
        "src.core.css_patcher.load_texture_name_map", lambda *_: {})


def test_pipeline_produces_summary_in_dry_run(tmp_path: Path, monkeypatch):
    css_dir = tmp_path / "skin"
    css_dir.mkdir(parents=True)
    (css_dir / "config.json").write_text("{}", encoding="utf-8")
    bundle_path = tmp_path / "ui_styles.bundle"
    bundle_path.write_bytes(b"orig")
    out_dir = tmp_path / "out"

    _setup_common_stubs(monkeypatch, dry_run=True)
    monkeypatch.setattr(
        "src.core.css_patcher.load_or_cache_config",
        lambda _: SimpleNamespace(includes=[]),
    )

    pipeline = SkinPatchPipeline(
        css_dir,
        out_dir,
        PipelineOptions(dry_run=True, use_scan_cache=False,
                        refresh_scan_cache=False),
    )

    result = pipeline.run(bundle=bundle_path)

    assert result.css_bundles_modified == 1
    assert result.summary_lines[0].startswith("Dry run summary")
    assert result.bundle_reports[0].dry_run is True
    assert result.bundle_reports[0].saved_path is None


def test_pipeline_texture_prefilter_invokes_swap(tmp_path: Path, monkeypatch):
    css_dir = tmp_path / "skin"
    css_dir.mkdir(parents=True)
    (css_dir / "config.json").write_text("{}", encoding="utf-8")
    bundle_path = tmp_path / "ui_icons.bundle"
    bundle_path.write_bytes(b"orig")
    out_dir = tmp_path / "out"

    _setup_common_stubs(monkeypatch, dry_run=False)
    monkeypatch.setattr(
        "src.core.css_patcher.load_or_cache_config",
        lambda *_: SimpleNamespace(includes=["assets/icons"]),
    )
    monkeypatch.setattr(
        "src.core.css_patcher.TextureSwapService", RecordingTextureSwapService)
    monkeypatch.setattr(
        "src.core.css_patcher._load_or_refresh_scan_cache",
        lambda *a, **k: {"FakeAsset"},
    )
    monkeypatch.setattr(
        "src.core.css_patcher.load_cached_bundle_index",
        lambda css_dir, bundle_path, skin_cache_dir=None: {
            "textures": ["IconHero"],
            "assets": ["FakeAsset"],
        },
    )
    monkeypatch.setattr(
        "src.core.css_patcher.load_texture_name_map",
        lambda *_: {"IconHero": "ui/icon"},
    )
    monkeypatch.setattr(
        "src.core.css_patcher.collect_replacement_stems",
        lambda *a, **k: ["iconhero"],
    )

    pipeline = SkinPatchPipeline(
        css_dir,
        out_dir,
        PipelineOptions(dry_run=False, use_scan_cache=True,
                        refresh_scan_cache=False),
    )

    result = pipeline.run(bundle=bundle_path)

    assert RecordingTextureSwapService.calls == [bundle_path]
    assert result.texture_replacements_total == 1
    assert result.texture_bundles_written == 1
    assert result.bundle_reports[0].texture_replacements == 1


def test_pipeline_texture_prefilter_skips_when_no_interest(tmp_path: Path, monkeypatch):
    css_dir = tmp_path / "skin"
    css_dir.mkdir(parents=True)
    (css_dir / "config.json").write_text("{}", encoding="utf-8")
    bundle_path = tmp_path / "ui_misc.bundle"
    bundle_path.write_bytes(b"orig")
    out_dir = tmp_path / "out"

    _setup_common_stubs(monkeypatch, dry_run=False)
    monkeypatch.setattr(
        "src.core.css_patcher.load_or_cache_config",
        lambda *_: SimpleNamespace(includes=["assets/icons"]),
    )
    monkeypatch.setattr(
        "src.core.css_patcher.TextureSwapService", RecordingTextureSwapService)
    monkeypatch.setattr(
        "src.core.css_patcher._load_or_refresh_scan_cache",
        lambda *a, **k: {"FakeAsset"},
    )
    monkeypatch.setattr(
        "src.core.css_patcher.load_cached_bundle_index",
        lambda css_dir, bundle_path, skin_cache_dir=None: {
            "textures": ["Another"]},
    )
    monkeypatch.setattr(
        "src.core.css_patcher.load_texture_name_map",
        lambda *_: {"IconHero": "ui/icon"},
    )
    monkeypatch.setattr(
        "src.core.css_patcher.collect_replacement_stems",
        lambda *a, **k: ["iconhero"],
    )

    pipeline = SkinPatchPipeline(
        css_dir,
        out_dir,
        PipelineOptions(dry_run=False, use_scan_cache=True,
                        refresh_scan_cache=False),
    )

    result = pipeline.run(bundle=bundle_path)

    assert RecordingTextureSwapService.calls == []
    assert result.texture_replacements_total == 0
    assert result.texture_bundles_written == 0
