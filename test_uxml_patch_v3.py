#!/usr/bin/env python3
"""Test UXML binary patching V3 - single bundle load to avoid caching."""

import sys
import logging
from pathlib import Path
import UnityPy

from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter
from fm_skin_builder.core.uxml.uxml_binary_patcher_v2 import UXMLBinaryPatcherV2

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def test_uxml_patch_v3():
    """Test UXML patching V3 with careful object handling."""
    # Paths
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    uxml_path = Path("test_skin_dir/panels/AboutClubCard.uxml")
    output_path = Path("test_output/ui-panelids-uxml_assets_all_v3.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    print(f"Loading UXML: {uxml_path}")
    importer = UXMLImporter()
    imported_data = importer.parse_uxml_to_dict(uxml_path)

    print(f"Imported {len(imported_data['m_VisualElementAssets'])} elements from UXML")

    # Find AboutClubCard - get metadata AND raw data in ONE pass
    patcher = UXMLBinaryPatcherV2(verbose=True)
    found = False
    target_obj = None
    raw_data = None
    visual_elements = []
    template_assets = []

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                # Use peek_name to avoid full deserialization
                name = obj.peek_name()
                if name == "AboutClubCard":
                    print(f"\n✓ Found VTA: {name}")
                    target_obj = obj
                    found = True

                    # Get raw data BEFORE calling read()
                    raw_data = obj.get_raw_data()
                    print(f"  → Raw data size: {len(raw_data)} bytes")

                    # NOW we can call read() to get metadata
                    # This is safe because we already got the raw data
                    data = obj.read()

                    if hasattr(data, "m_VisualElementAssets"):
                        visual_elements = list(data.m_VisualElementAssets)
                        print(f"  → Has {len(visual_elements)} visual elements")
                    if hasattr(data, "m_TemplateAssets"):
                        template_assets = list(data.m_TemplateAssets)
                        print(f"  → Has {len(template_assets)} template assets")

                    break
            except Exception as e:
                print(f"  Error: {e}")
                pass

    if not found or target_obj is None or raw_data is None:
        print("\nERROR: AboutClubCard VTA not found in bundle!")
        return False

    # Apply patch with separate arrays
    print("  → Patching AboutClubCard with V2 patcher")
    new_raw_data = patcher.apply_uxml_to_vta_binary(
        raw_data, imported_data, visual_elements, template_assets
    )

    if new_raw_data:
        print(f"  → Patch successful! New size: {len(new_raw_data)} bytes")

        # CRITICAL: Set the raw data on the SAME object we got it from
        target_obj.set_raw_data(new_raw_data)

        # Save the modified bundle
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(env.file.save())

        print(f"\n✅ Saved modified bundle to: {output_path}")
        return True
    else:
        print("  → Patch failed!")
        return False

if __name__ == "__main__":
    success = test_uxml_patch_v3()
    sys.exit(0 if success else 1)
