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

    # First pass: find AboutClubCard without calling read()
    target_obj = None
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                name = obj.peek_name()
                if name == "AboutClubCard":
                    print(f"\n✓ Found VTA: {name} (using peek_name)")
                    target_obj = obj
                    found = True
                    break
            except:
                pass

    if target_obj is None:
        print("\nERROR: AboutClubCard VTA not found in bundle!")
        return False

    # Second pass: load a SEPARATE instance to get metadata WITHOUT corrupting target_obj
    env2 = UnityPy.load(str(bundle_path))
    visual_elements = []
    template_assets = []

    for obj2 in env2.objects:
        if obj2.type.name == "MonoBehaviour":
            try:
                name = obj2.peek_name()
                if name == "AboutClubCard":
                    # Read from this SEPARATE object to get metadata
                    data = obj2.read()
                    if hasattr(data, "m_VisualElementAssets"):
                        visual_elements = list(data.m_VisualElementAssets)
                        print(f"  → Has {len(visual_elements)} visual elements")
                    if hasattr(data, "m_TemplateAssets"):
                        template_assets = list(data.m_TemplateAssets)
                        print(f"  → Has {len(template_assets)} template assets")
                    break
            except:
                pass

    # Get raw binary data from target_obj (without calling read() on it!)
    raw_data = target_obj.get_raw_data()
    print(f"  → Raw data size: {len(raw_data)} bytes")

    # Apply patch with separate arrays
    print("  → Patching AboutClubCard with V2 patcher")
    new_raw_data = patcher.apply_uxml_to_vta_binary(
        raw_data, imported_data, visual_elements, template_assets
    )

    if new_raw_data:
        print(f"  → Patch successful! New size: {len(new_raw_data)} bytes")
        target_obj.set_raw_data(new_raw_data)
    else:
        print("  → Patch failed!")
        return False

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
