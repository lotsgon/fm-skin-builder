#!/usr/bin/env python3
"""
Import UXML files and patch a Unity bundle.

Usage:
    python import_uxml.py --bundle ui.unity3d --uxml edited_uxml --out patched_ui.unity3d

This will read edited UXML files and update the corresponding VisualTreeAssets in the bundle.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_skin_builder.core.unity.asset_bundle import AssetBundle
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.logger import get_logger

log = get_logger(__name__)


def import_uxml_to_bundle(
    bundle_path: Path, uxml_dir: Path, output_bundle: Path, backup: bool = True
) -> int:
    """
    Import edited UXML files back into a bundle.

    Args:
        bundle_path: Path to original Unity bundle
        uxml_dir: Directory containing edited UXML files
        output_bundle: Path for output (modified) bundle
        backup: Create .bak backup of original

    Returns:
        Number of VTA assets modified
    """
    log.info(f"Loading bundle: {bundle_path}")

    if not bundle_path.exists():
        log.error(f"Bundle not found: {bundle_path}")
        return 0

    if not uxml_dir.exists() or not uxml_dir.is_dir():
        log.error(f"UXML directory not found: {uxml_dir}")
        return 0

    # Backup original bundle
    if backup and bundle_path != output_bundle:
        backup_path = bundle_path.with_suffix(bundle_path.suffix + ".bak")
        if not backup_path.exists():
            import shutil

            shutil.copy2(bundle_path, backup_path)
            log.info(f"Backup created: {backup_path}")

    bundle = AssetBundle.from_file(bundle_path)
    importer = UXMLImporter()
    modified_count = 0

    # Find all VisualTreeAssets and update them
    for obj in bundle.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.read()
            type_name = getattr(data, "m_ClassName", None)

            if type_name == "UnityEngine.UIElements.VisualTreeAsset":
                asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")
                if not asset_name:
                    asset_name = f"VTA_{obj.path_id}"

                # Check if we have a modified UXML for this asset
                uxml_file = uxml_dir / f"{asset_name}.uxml"

                if uxml_file.exists():
                    log.info(f"  Importing: {asset_name}")

                    try:
                        # Import UXML
                        doc = importer.import_uxml(uxml_file)

                        # Convert back to VTA structure
                        vta_structure = importer.build_visual_tree_asset(doc)

                        # Update the object's data
                        for key, value in vta_structure.items():
                            setattr(data, key, value)

                        # Write updated data back to object
                        obj.save_typetree(data)

                        modified_count += 1

                    except Exception as e:
                        log.error(f"     Failed to import {asset_name}: {e}")

    # Save modified bundle
    log.info(f"\nSaving modified bundle to: {output_bundle}")
    output_bundle.parent.mkdir(exist_ok=True, parents=True)
    bundle.save(output_bundle)

    log.info(f"\n✅ Modified {modified_count} VTA assets")
    log.info(f"✅ Bundle saved: {output_bundle}")

    return modified_count


def main():
    parser = argparse.ArgumentParser(
        description="Import UXML files and patch a Unity bundle"
    )
    parser.add_argument(
        "--bundle", type=Path, required=True, help="Path to Unity bundle file to patch"
    )
    parser.add_argument(
        "--uxml",
        type=Path,
        required=True,
        help="Directory containing edited UXML files",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="Output path for patched bundle"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of original bundle",
    )

    args = parser.parse_args()

    count = import_uxml_to_bundle(
        args.bundle, args.uxml, args.out, backup=not args.no_backup
    )

    if count == 0:
        log.warning("No UXML files were imported (no matching assets found)")
        sys.exit(1)


if __name__ == "__main__":
    main()
