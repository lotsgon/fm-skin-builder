"""
Catalogue Command

CLI command for building asset catalogues from FM bundles.
"""

from __future__ import annotations
import os
from pathlib import Path
from argparse import Namespace
from typing import Optional, Dict

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

    # Pretty-print JSON flag
    pretty = getattr(args, "pretty", False)

    # Dry-run flag
    dry_run = getattr(args, "dry_run", False)

    # Previous version override
    previous_version = getattr(args, "previous_version", None)

    # No changelog flag
    skip_changelog = getattr(args, "no_changelog", False)

    # R2 configuration
    r2_config = {}
    if hasattr(args, 'r2_endpoint') and args.r2_endpoint:
        r2_config['endpoint'] = args.r2_endpoint
        r2_config['bucket'] = args.r2_bucket or os.environ.get('R2_BUCKET')
        r2_config['access_key'] = args.r2_access_key or os.environ.get('R2_ACCESS_KEY')
        r2_config['secret_key'] = args.r2_secret_key or os.environ.get('R2_SECRET_KEY')
        r2_config['base_path'] = os.environ.get('R2_BASE_PATH', '')

        if not r2_config['bucket']:
            log.warning("R2 endpoint specified but no bucket provided")
            r2_config = {}

    # Get icon paths
    icon_white = (
        Path(__file__).parent.parent.parent.parent / "icons" / "SVG" / "White.svg"
    )
    icon_black = (
        Path(__file__).parent.parent.parent.parent / "icons" / "SVG" / "Black.svg"
    )

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
            pretty_json=pretty,
            previous_version=previous_version,
            skip_changelog=skip_changelog,
            r2_config=r2_config if r2_config else None,
        )

        if dry_run:
            log.info(f"Would build catalogue for FM {fm_version}")
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
