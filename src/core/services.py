from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Set, Tuple, TYPE_CHECKING

from .context import BundleContext, PatchReport
from .textures import swap_textures, TextureSwapResult

if TYPE_CHECKING:  # pragma: no cover - circular import safe typing
    from .css_patcher import CssPatcher


@dataclass
class CssPatchOptions:
    patch_direct: bool = False
    debug_export_dir: Optional[Path] = None
    dry_run: bool = False
    selectors_filter: Optional[Set[str]] = None
    selector_props_filter: Optional[Set[Tuple[str, str]]] = None


class CssPatchService:
    """Thin facade around :class:`CssPatcher` for pipeline orchestration."""

    def __init__(
        self,
        css_vars: Dict[str, str],
        selector_overrides: Dict[Tuple[str, str], str],
        options: CssPatchOptions,
    ) -> None:
        self._css_vars = css_vars
        self._selector_overrides = selector_overrides
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
                self._css_vars,
                self._selector_overrides,
                patch_direct=self._options.patch_direct,
                debug_export_dir=self._options.debug_export_dir,
                dry_run=self._options.dry_run,
                selectors_filter=self._options.selectors_filter,
                selector_props_filter=self._options.selector_props_filter,
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

    def apply(
        self,
        bundle: BundleContext,
        skin_dir: Path,
        out_dir: Path,
        report: PatchReport,
    ) -> TextureSwapResult:
        if not self._should_swap():
            return TextureSwapResult(0, None)

        bundle.load()
        result: TextureSwapResult = swap_textures(
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
            if not self.options.dry_run:
                bundle.mark_dirty()
        return result

    def _should_swap(self) -> bool:
        includes = {x.lower() for x in self.options.includes}
        return any(
            token in includes for token in {"assets/icons", "assets/backgrounds"}
        )
