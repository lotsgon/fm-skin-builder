from __future__ import annotations
from pathlib import Path
from ...core.css_patcher import run_patch
from ...core.logger import get_logger


log = get_logger(__name__)


def run(args) -> None:
    css_dir = Path(args.css)
    out_dir = Path(args.out)
    bundle = Path(args.bundle) if args.bundle else None
    result = run_patch(
        css_dir=css_dir,
        out_dir=out_dir,
        bundle=bundle,
        patch_direct=args.patch_direct,
        debug_export=args.debug_export,
        backup=args.backup,
        dry_run=args.dry_run,
        use_scan_cache=not args.no_scan_cache,
        refresh_scan_cache=args.refresh_scan_cache,
    )

    if result.summary_lines:
        for line in result.summary_lines:
            log.info(line)

    log.info("\n=== Overall Summary ===")
    log.info("Bundles processed: %s", result.bundles_requested)
    log.info("CSS bundles modified: %s", result.css_bundles_modified)
    if result.texture_replacements_total or result.texture_bundles_written:
        if args.dry_run:
            log.info(
                "[DRY-RUN] Would replace %s textures across bundles",
                result.texture_replacements_total,
            )
        else:
            log.info(
                "Textures replaced: %s across %s bundles",
                result.texture_replacements_total,
                result.texture_bundles_written,
            )
