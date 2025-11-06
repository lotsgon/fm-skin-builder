from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .context import BundleContext, PatchReport
from .textures import swap_textures, TextureSwapResult


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
