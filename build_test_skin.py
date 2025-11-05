"""
Build test_skin with UXML overrides.
"""

from src.core.logger import get_logger
from src.utils.uxml_importer import UXMLImporter
from src.core.bundle_manager import BundleManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


logger = get_logger(__name__)


def build_test_skin():
    """Build test_skin bundles with UXML overrides."""

    skin_dir = Path("skins/test_skin")
    output_dir = Path("build/test_skin")

    # UXML files to patch
    uxml_overrides = {
        "PlayerAttributesStandardBlock": "uxml/PlayerAttributesStandardBlock.uxml",
        "PlayerAttributesCompactBlock": "uxml/PlayerAttributesCompactBlock.uxml",
        "PlayerAttributesLargeBlock": "uxml/PlayerAttributesLargeBlock.uxml",
        "PlayerAttributesSmallBlock": "uxml/PlayerAttributesSmallBlock.uxml",
    }

    # These UXML assets are in ui-tiles bundle
    source_bundle = Path("bundles/ui-tiles_assets_all.bundle")
    output_bundle = output_dir / "ui-tiles_assets_all.bundle"

    logger.info("=" * 60)
    logger.info("Building Test Skin with UXML Overrides")
    logger.info("=" * 60)
    logger.info(f"Source: {source_bundle}")
    logger.info(f"Output: {output_bundle}")
    logger.info("")

    # Load bundle
    logger.info("Loading bundle...")
    bundle = BundleManager(source_bundle)

    # Parse and apply each UXML override
    importer = UXMLImporter()

    for asset_name, uxml_path in uxml_overrides.items():
        full_path = skin_dir / uxml_path

        if not full_path.exists():
            logger.warning(f"UXML file not found: {full_path}")
            continue

        logger.info(f"Processing {asset_name}...")

        # Parse UXML
        uxml_data = importer.parse_uxml_file(str(full_path))

        if uxml_data is None:
            logger.error(f"  Failed to parse {uxml_path}")
            continue

        # Check for errors
        if importer.errors:
            logger.warning(f"  Validation issues:")
            for error in importer.errors:
                logger.warning(
                    f"    {error.severity.upper()}: {error.message}")

        logger.info(
            f"  Parsed {len(uxml_data['m_VisualElementAssets'])} elements")

        # Apply to bundle
        success = bundle.update_uxml_asset(asset_name, uxml_data, full_path)

        if success:
            logger.info(f"  ✓ Applied {asset_name}")
        else:
            logger.error(f"  ✗ Failed to apply {asset_name}")

    # Save bundle
    logger.info("")
    logger.info("Saving bundle...")
    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.save(output_bundle)

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Build Complete!")
    logger.info("=" * 60)
    logger.info(f"Output: {output_bundle}")
    logger.info(f"Size:   {output_bundle.stat().st_size:,} bytes")
    logger.info("")
    logger.info("To test in FM24:")
    logger.info(f"  cp {output_bundle} /path/to/FM24/data/")
    logger.info("=" * 60)

    return True


if __name__ == '__main__':
    import os
    success = build_test_skin()
    # Force immediate exit to avoid UnityPy cleanup crash
    os._exit(0 if success else 1)
