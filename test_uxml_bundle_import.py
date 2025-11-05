"""Test UXML import into bundle."""

from src.core.logger import get_logger
from src.utils.uxml_importer import UXMLImporter
from src.core.bundle_manager import BundleManager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


log = get_logger(__name__)


def test_uxml_import():
    """Test importing UXML and writing to bundle."""

    # Load the bundle
    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    output_path = Path("build/ui-tiles_assets_all_modified.bundle")

    log.info(f"Loading bundle: {bundle_path}")
    bundle = BundleManager(bundle_path)
    bundle.load_bundle()

    # Import UXML file
    uxml_file = Path("skins/test_uxml_import/uxml/PlayerAttributesTile.uxml")

    log.info(f"Importing UXML: {uxml_file}")
    importer = UXMLImporter()
    uxml_data = importer.parse_uxml_file(str(uxml_file))

    # Show validation
    print("\n" + importer.get_validation_report())

    # Update bundle
    log.info("\nUpdating bundle with UXML data...")
    success = bundle.update_uxml_asset("PlayerAttributesTile", uxml_data)

    if success:
        log.info("✓ UXML asset updated successfully")

        # Save modified bundle
        log.info(f"\nSaving to: {output_path}")
        bundle.save(output_path)
        log.info("✓ Bundle saved!")

        print(f"\n✅ Success! Modified bundle saved to: {output_path}")
        print(f"   Original: {bundle_path.stat().st_size:,} bytes")
        print(f"   Modified: {output_path.stat().st_size:,} bytes")
    else:
        log.error("✗ Failed to update UXML asset")
        return False

    return True


if __name__ == '__main__':
    try:
        test_uxml_import()
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
