from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Set, Tuple, TYPE_CHECKING, DefaultDict, List

from .context import BundleContext, PatchReport
from .textures import (
    swap_textures,
    TextureSwapResult,
    apply_dynamic_sprite_rebinds,
    DynamicSpriteRebind,
)
from .css_sources import CollectedCss
from .font_swap_service import FontSwapService, FontSwapOptions, FontSwapResult

if TYPE_CHECKING:  # pragma: no cover - circular import safe typing
    from .css_patcher import CssPatcher


@dataclass
class CssPatchOptions:
    patch_direct: bool = False
    debug_export_dir: Optional[Path] = None
    dry_run: bool = False
    selectors_filter: Optional[Set[str]] = None
    selector_props_filter: Optional[Set[Tuple[str, str]]] = None
    primary_variable_stylesheet: Optional[str] = None
    primary_selector_stylesheet: Optional[str] = None


class CssPatchService:
    """Thin facade around :class:`CssPatcher` for pipeline orchestration."""

    def __init__(
        self,
        css_data: CollectedCss,
        options: CssPatchOptions,
    ) -> None:
        self._css_data = css_data
        self._options = options
        self._patcher: Optional["CssPatcher"] = None

    def apply(
        self,
        bundle: BundleContext,
        *,
        candidate_assets: Optional[Set[str]] = None,
    ) -> PatchReport:
        patcher = self._ensure_patcher()
        return patcher.patch_bundle(bundle, candidate_assets=candidate_assets)

    def _ensure_patcher(self) -> "CssPatcher":
        if self._patcher is None:
            from .css_patcher import CssPatcher  # local import to avoid cycle

            self._patcher = CssPatcher(
                self._css_data,
                patch_direct=self._options.patch_direct,
                debug_export_dir=self._options.debug_export_dir,
                dry_run=self._options.dry_run,
                selectors_filter=self._options.selectors_filter,
                selector_props_filter=self._options.selector_props_filter,
                primary_variable_stylesheet=self._options.primary_variable_stylesheet,
                primary_selector_stylesheet=self._options.primary_selector_stylesheet,
            )
        return self._patcher


@dataclass
class TextureSwapOptions:
    includes: Sequence[str]
    dry_run: bool = False


class TextureSwapService:
    """Facade around texture swapping that updates a PatchReport."""

    def __init__(self, options: TextureSwapOptions):
        self.options = options
        self._includes_lower = [inc.lower() for inc in options.includes]
        # Dynamic Sprite Replacement (SIImage Fix): queue rebind jobs for paired bundles.
        self._pending_dynamic_jobs: DefaultDict[str, List[DynamicSpriteRebind]] = (
            defaultdict(list)
        )

    def has_pending_jobs(self, bundle_name: str) -> bool:
        return bool(self._pending_dynamic_jobs.get(bundle_name.lower(), []))

    def apply(
        self,
        bundle: BundleContext,
        skin_dir: Path,
        out_dir: Path,
        report: PatchReport,
    ) -> TextureSwapResult:
        bundle_key = bundle.bundle_path.name.lower()
        pending_jobs = self._pending_dynamic_jobs.pop(bundle_key, [])
        should_swap = self._should_swap()

        if not should_swap and not pending_jobs:
            return TextureSwapResult(0, None, {})

        bundle.load()

        pointer_updates_total = apply_dynamic_sprite_rebinds(bundle.env, pending_jobs)

        result: TextureSwapResult = TextureSwapResult(0, None, {})
        if should_swap:
            result = swap_textures(
                bundle_path=bundle.bundle_path,
                skin_dir=skin_dir,
                includes=list(self.options.includes),
                out_dir=out_dir,
                dry_run=self.options.dry_run,
                env=bundle.env,
                defer_save=True,
            )
            if result.replaced_count:
                report.texture_replacements += result.replaced_count

        immediate_jobs: List[DynamicSpriteRebind] = []
        for target_name, job_list in result.dynamic_sprite_jobs.items():
            target_key = target_name.lower()
            if target_key == bundle_key:
                immediate_jobs.extend(job_list)
            else:
                self._pending_dynamic_jobs[target_key].extend(job_list)

        if immediate_jobs:
            pointer_updates_total += apply_dynamic_sprite_rebinds(
                bundle.env, immediate_jobs
            )

        if pointer_updates_total:
            report.texture_replacements += pointer_updates_total

        total_swaps = result.replaced_count + pointer_updates_total
        if total_swaps and not self.options.dry_run:
            bundle.mark_dirty()

        return TextureSwapResult(total_swaps, result.out_file, {})

    def _should_swap(self) -> bool:
        return any(
            token in self._includes_lower
            for token in {"assets/icons", "assets/backgrounds"}
        )
