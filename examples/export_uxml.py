#!/usr/bin/env python3
"""
Export UXML files from a Unity bundle.

Usage:
    python export_uxml.py --bundle path/to/ui.unity3d --out exported_uxml

This will export all VisualTreeAssets as human-readable UXML files.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_skin_builder.core.unity.asset_bundle import AssetBundle
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter
from fm_skin_builder.core.logger import get_logger

log = get_logger(__name__)


def export_all_uxml(bundle_path: Path, output_dir: Path) -> int:
    """
    Export all VisualTreeAssets from a bundle as UXML files.

    Args:
        bundle_path: Path to Unity bundle file
        output_dir: Directory to save UXML files

    Returns:
        Number of UXML files exported
    """
    log.info(f"Loading bundle: {bundle_path}")

    if not bundle_path.exists():
        log.error(f"Bundle not found: {bundle_path}")
        return 0

    bundle = AssetBundle.from_file(bundle_path)

    # Create output directory
    output_dir.mkdir(exist_ok=True, parents=True)
    log.info(f"Output directory: {output_dir}")

    # Find all VisualTreeAssets
    vta_count = 0
    exporter = UXMLExporter()

    for obj in bundle.objects:
        if obj.type.name == "MonoBehaviour":
            # Check if it's a VisualTreeAsset
            data = obj.read()
            type_name = getattr(data, "m_ClassName", None)

            if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                vta_count += 1

                # Generate filename from object name or ID
                asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                if not asset_name:
                    asset_name = f"VTA_{obj.path_id}"

                # Export to UXML
                output_file = output_dir / f"{asset_name}.uxml"
                log.info(f"  [{vta_count}] Exporting: {asset_name}")

                try:
                    doc = exporter.export_visual_tree_asset(data, asset_name=asset_name)
                    exporter.write_uxml(doc, output_file)
                except Exception as e:
                    log.error(f"     Failed to export {asset_name}: {e}")

    log.info(f"\n✅ Exported {vta_count} UXML files to {output_dir}")
    return vta_count


def main():
    parser = argparse.ArgumentParser(
        description="Export UXML files from a Unity bundle"
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
        help="Path to Unity bundle file (e.g., ui.unity3d)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("exported_uxml"),
        help="Output directory for UXML files (default: exported_uxml)"
    )

    args = parser.parse_args()

    count = export_all_uxml(args.bundle, args.out)

    if count == 0:
        log.warning("No VisualTreeAssets found in bundle")
        sys.exit(1)


if __name__ == "__main__":
    main()
