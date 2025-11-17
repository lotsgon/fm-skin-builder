#!/usr/bin/env python3
"""Test script for UXML binary patching."""

import sys
import logging
from pathlib import Path
import UnityPy

from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.uxml.uxml_binary_patcher import UXMLBinaryPatcher

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_uxml_patch():
    """Test UXML patching on AboutClubCard."""
    # Paths
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    uxml_path = Path("test_skin_dir/panels/AboutClubCard.uxml")
    output_path = Path("test_output/ui-panelids-uxml_assets_all.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    print(f"Loading UXML: {uxml_path}")
    importer = UXMLImporter()
    imported_data = importer.parse_uxml_to_dict(uxml_path)

    print(f"Imported {len(imported_data['m_VisualElementAssets'])} elements from UXML")
    for i, elem in enumerate(imported_data['m_VisualElementAssets']):
        print(f"  Imported element {i}: ID={elem['m_Id']}, classes={elem['m_Classes']}")

    # Find the CalendarTool VTA
    patcher = UXMLBinaryPatcher(verbose=True)
    found = False

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or
                         hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")

                    if asset_name == "AboutClubCard":
                        print(f"\n✓ Found VTA: {asset_name}")
                        found = True
                        print("  → Patching AboutClubCard")

                        # Get original elements
                        original_elements = []
                        if hasattr(data, "m_VisualElementAssets"):
                            original_elements.extend(list(data.m_VisualElementAssets))
                            print(f"  → Has {len(data.m_VisualElementAssets)} visual elements")
                        if hasattr(data, "m_TemplateAssets"):
                            original_elements.extend(list(data.m_TemplateAssets))
                            print(f"  → Has {len(data.m_TemplateAssets)} template assets")

                        # Get raw binary data
                        raw_data = obj.get_raw_data()
                        print(f"  → Raw data size: {len(raw_data)} bytes")

                        # Apply patch
                        new_raw_data = patcher.apply_uxml_to_vta_binary(
                            raw_data, imported_data, original_elements
                        )

                        if new_raw_data:
                            print(f"  → Patch successful! New size: {len(new_raw_data)} bytes")
                            obj.set_raw_data(new_raw_data)
                        else:
                            print("  → Patch failed!")
                            return False

            except Exception:
                pass

    if not found:
        print("\nERROR: AboutClubCard VTA not found in bundle!")
        return False

    # Save the modified bundle
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(env.file.save())

    print(f"\n✅ Saved modified bundle to: {output_path}")
    return True

if __name__ == "__main__":
    success = test_uxml_patch()
    sys.exit(0 if success else 1)
