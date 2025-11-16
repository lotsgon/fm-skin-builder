#!/usr/bin/env python3
"""Test script for UXML binary patching V2 with separate arrays."""

import sys
import logging
from pathlib import Path
import UnityPy

from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.uxml.uxml_binary_patcher_v2 import UXMLBinaryPatcherV2

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_uxml_patch_v2():
    """Test UXML patching V2 on AboutClubCard."""
    # Paths
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    uxml_path = Path("test_skin_dir/panels/AboutClubCard.uxml")
    output_path = Path("test_output/ui-panelids-uxml_assets_all_v2.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    print(f"Loading UXML: {uxml_path}")
    importer = UXMLImporter()
    imported_data = importer.parse_uxml_to_dict(uxml_path)

    print(f"Imported {len(imported_data['m_VisualElementAssets'])} elements from UXML")
    for i, elem in enumerate(imported_data['m_VisualElementAssets']):
        print(f"  Imported element {i}: ID={elem['m_Id']}, classes={elem['m_Classes']}")

    # Find the AboutClubCard VTA
    patcher = UXMLBinaryPatcherV2(verbose=True)
    found = False

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or
                         hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    asset_name = getattr(data, "m_Name", "")

                    if asset_name == "AboutClubCard":
                        print(f"\n✓ Found VTA: {asset_name}")
                        found = True
                        print(f"  → Patching AboutClubCard with V2 patcher")

                        # Get separate arrays
                        visual_elements = []
                        template_assets = []
                        if hasattr(data, "m_VisualElementAssets"):
                            visual_elements = list(data.m_VisualElementAssets)
                            print(f"  → Has {len(visual_elements)} visual elements")
                        if hasattr(data, "m_TemplateAssets"):
                            template_assets = list(data.m_TemplateAssets)
                            print(f"  → Has {len(template_assets)} template assets")

                        # Get raw binary data
                        raw_data = obj.get_raw_data()
                        print(f"  → Raw data size: {len(raw_data)} bytes")

                        # Apply patch with separate arrays
                        new_raw_data = patcher.apply_uxml_to_vta_binary(
                            raw_data, imported_data, visual_elements, template_assets
                        )

                        if new_raw_data:
                            print(f"  → Patch successful! New size: {len(new_raw_data)} bytes")
                            obj.set_raw_data(new_raw_data)
                        else:
                            print(f"  → Patch failed!")
                            return False

            except Exception as e:
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
    success = test_uxml_patch_v2()
    sys.exit(0 if success else 1)
