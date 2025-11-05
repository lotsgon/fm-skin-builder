"""
Quick test script to build a single UXML-patched bundle.
"""

from src.core.logger import get_logger
from src.utils.uxml_importer import UXMLImporter
from src.core.bundle_manager import BundleManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


logger = get_logger(__name__)


def build_uxml_test_bundle():
    """Build test bundle with UXML override."""

    # Paths
    source_bundle = Path("bundles/ui-tiles_assets_all.bundle")
    uxml_file = Path("skins/test_uxml_import/uxml/PlayerAttributesTile.uxml")
    output_bundle = Path("build/ui-tiles_assets_all_modified.bundle")

    # Validate inputs
    if not source_bundle.exists():
        logger.error(f"Source bundle not found: {source_bundle}")
        return False

    if not uxml_file.exists():
        logger.error(f"UXML file not found: {uxml_file}")
        return False

    logger.info("=" * 60)
    logger.info("Building UXML Test Bundle")
    logger.info("=" * 60)
    logger.info(f"Source: {source_bundle}")
    logger.info(f"UXML:   {uxml_file}")
    logger.info(f"Output: {output_bundle}")
    logger.info("")

    # Load bundle
    logger.info("Loading bundle...")
    bundle = BundleManager(source_bundle)

    # Parse UXML
    logger.info("Parsing UXML...")
    importer = UXMLImporter()
    uxml_data = importer.parse_uxml_file(str(uxml_file))

    if uxml_data is None:
        logger.error("Failed to parse UXML")
        return False

    # Check validation
    validation = importer.get_validation_report()
    if importer.errors:
        logger.error("UXML validation failed:")
        logger.error(validation)
        return False

    logger.info(f"✓ Parsed {len(uxml_data['m_VisualElementAssets'])} elements")

    # Apply UXML override
    logger.info("Applying UXML override...")
    success = bundle.update_uxml_asset("PlayerAttributesTile", uxml_data)

    if not success:
        logger.error("Failed to update UXML asset")
        return False

    # Save bundle
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
    logger.info("Next steps:")
    logger.info("1. Copy to FM24 data folder:")
    logger.info(f"   cp {output_bundle} /path/to/FM24/data/")
    logger.info("2. Launch game and test")
    logger.info("=" * 60)

    return True


if __name__ == '__main__':
    success = build_uxml_test_bundle()
    sys.exit(0 if success else 1)
