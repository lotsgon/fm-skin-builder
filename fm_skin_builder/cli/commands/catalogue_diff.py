"""
Catalogue Diff Command

CLI command for comparing two catalogue versions and generating changelogs.
"""

from __future__ import annotations
from pathlib import Path
from argparse import Namespace
import json

from ...core.catalogue.version_differ import VersionDiffer
from ...core.logger import get_logger


log = get_logger(__name__)


def run(args: Namespace) -> None:
    """
    Run catalogue diff command.

    Args:
        args: Parsed command-line arguments
    """
    # Get paths
    old_dir = Path(args.old)
    new_dir = Path(args.new)
    out_dir = Path(args.out) if args.out else new_dir

    # Validate paths
    if not old_dir.exists():
        log.error(f"Old catalogue directory does not exist: {old_dir}")
        return

    if not new_dir.exists():
        log.error(f"New catalogue directory does not exist: {new_dir}")
        return

    # Check for required files
    required_files = [
        "metadata.json",
        "css-variables.json",
        "css-classes.json",
        "sprites.json",
        "textures.json",
        "fonts.json",
    ]

    for file in required_files:
        if not (old_dir / file).exists():
            log.error(f"Missing file in old catalogue: {file}")
            return
        if not (new_dir / file).exists():
            log.error(f"Missing file in new catalogue: {file}")
            return

    # Pretty-print JSON flag
    pretty = getattr(args, "pretty", False)

    try:
        log.info("Comparing catalogues:")
        log.info(f"  Old: {old_dir}")
        log.info(f"  New: {new_dir}")

        # Create differ and compare
        differ = VersionDiffer(old_dir, new_dir)
        differ.load_catalogues()
        changelog = differ.compare()

        # Save changelog as JSON
        out_dir.mkdir(parents=True, exist_ok=True)
        changelog_path = out_dir / "changelog.json"

        with open(changelog_path, "w", encoding="utf-8") as f:
            indent = 2 if pretty else None
            json.dump(changelog, f, ensure_ascii=False, indent=indent)

        log.info(f"✅ Changelog saved: {changelog_path}")

        # Also generate HTML report
        html_report = differ.generate_html_report(changelog)
        html_path = out_dir / "changelog.html"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_report)

        log.info(f"✅ HTML report saved: {html_path}")

        # Print summary
        log.info("\nSummary:")
        for asset_type, stats in changelog["summary"].items():
            if stats["total"] > 0:
                display_name = asset_type.replace("_", " ").title()
                log.info(f"  {display_name}:")
                log.info(f"    Added: {stats['added']}")
                log.info(f"    Removed: {stats['removed']}")
                log.info(f"    Modified: {stats['modified']}")

    except Exception as e:
        log.error(f"Failed to generate changelog: {e}")
        import traceback

        traceback.print_exc()
