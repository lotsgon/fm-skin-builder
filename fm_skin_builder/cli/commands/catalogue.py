"""
Catalogue Command

CLI command for building asset catalogues from FM bundles.
"""

from __future__ import annotations
from pathlib import Path
from argparse import Namespace

from ...core.catalogue.builder import CatalogueBuilder
from ...core.logger import get_logger


log = get_logger(__name__)


def run(args: Namespace) -> None:
    """
    Run catalogue building command.

    Args:
        args: Parsed command-line arguments
    """
    # Get bundle path(s)
    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        log.error(f"Bundle path does not exist: {bundle_path}")
        return

    # Get output directory
    output_dir = Path(args.out)

    # Get FM version
    fm_version = args.fm_version

    # Get catalogue version (default: 1)
    catalogue_version = getattr(args, 'catalogue_version', 1)

    # Pretty-print JSON flag
    pretty = getattr(args, 'pretty', False)

    # Dry-run flag
    dry_run = getattr(args, 'dry_run', False)

    # Get icon paths
    icon_white = Path(__file__).parent.parent.parent.parent / "icons" / "SVG" / "White.svg"
    icon_black = Path(__file__).parent.parent.parent.parent / "icons" / "SVG" / "Black.svg"

    if not icon_white.exists():
        log.warning(f"White icon not found: {icon_white}")
        log.warning("Thumbnails will be generated without watermarks")

    if dry_run:
        log.info("DRY RUN - No files will be written")

    try:
        # Create builder
        builder = CatalogueBuilder(
            fm_version=fm_version,
            output_dir=output_dir,
            icon_white_path=icon_white,
            icon_black_path=icon_black,
            catalogue_version=catalogue_version,
            pretty_json=pretty,
        )

        if dry_run:
            log.info(f"Would build catalogue for FM {fm_version} v{catalogue_version}")
            log.info(f"Would scan: {bundle_path}")
            log.info(f"Would output to: {builder.output_dir}")
            return

        # Build catalogue
        bundles = [bundle_path]
        builder.build(bundles)

    except Exception as e:
        log.error(f"Failed to build catalogue: {e}")
        import traceback
        traceback.print_exc()
