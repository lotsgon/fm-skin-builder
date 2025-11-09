#!/usr/bin/env python3
"""Test script for vector sprite integration in the main patching system."""

from fm_skin_builder.core.textures import swap_textures
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

log = logging.getLogger(__name__)

# Import the texture swapping function

# Force debug on textures module
textures_log = logging.getLogger("fm_skin_builder.core.textures")
textures_log.setLevel(logging.DEBUG)
for handler in textures_log.handlers:
    handler.setLevel(logging.DEBUG)


def main():
    # Paths
    skin_dir = Path("skins/test_skin")
    out_dir = Path("build")

    if not skin_dir.exists():
        log.error(f"Skin directory not found: {skin_dir}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 80)
    log.info("Testing Vector Sprite Integration - ALL SCALES")
    log.info("=" * 80)
    log.info(f"Skin: {skin_dir}")
    log.info(f"Output: {out_dir}")
    log.info("=" * 80)

    # Test all scales
    total_replaced = 0
    for scale in ["1x", "2x", "3x", "4x"]:
        bundle_path = Path(f"bundles/ui-icons_assets_{scale}.bundle")

        if not bundle_path.exists():
            log.warning(f"Bundle not found: {bundle_path}")
            continue

        log.info(f"\n--- Processing {scale} bundle ---")

        # Run the swap with icons included
        result = swap_textures(
            bundle_path=bundle_path,
            skin_dir=skin_dir,
            includes=["assets/icons"],
            out_dir=out_dir,
            dry_run=False
        )

        log.info(f"{scale}: {result.replaced_count} replacements")
        total_replaced += result.replaced_count

    log.info("=" * 80)
    log.info(f"TOTAL: {total_replaced} replacements across all scales")
    log.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
