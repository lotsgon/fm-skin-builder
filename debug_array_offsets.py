#!/usr/bin/env python3
"""Debug script to find exact array offsets and type info locations."""

from pathlib import Path
import struct
import UnityPy

def debug_arrays():
    """Find exact locations of arrays and type info."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    asset_name = getattr(data, "m_Name", "")
                    if asset_name == "AboutClubCard":
                        raw_data = obj.get_raw_data()

                        print("=== Array Offset Analysis ===\n")
                        print(f"Raw data size: {len(raw_data)} bytes\n")

                        # Visual elements
                        print("Visual Elements:")
                        print(f"  Element 0 ID: {data.m_VisualElementAssets[0].m_Id}")
                        print(f"  Element 1 ID: {data.m_VisualElementAssets[1].m_Id}")

                        # Find them in binary
                        elem0_offset = raw_data.find(struct.pack('<i', data.m_VisualElementAssets[0].m_Id))
                        elem1_offset = raw_data.find(struct.pack('<i', data.m_VisualElementAssets[1].m_Id))

                        print(f"  Element 0 offset: {elem0_offset}")
                        print(f"  Element 1 offset: {elem1_offset}")
                        print(f"  Element 1 ends around: 389 (from previous analysis)")

                        # Template assets
                        print(f"\nTemplate Assets:")
                        print(f"  Template 0 ID: {data.m_TemplateAssets[0].m_Id}")

                        template_offset = raw_data.find(struct.pack('<i', data.m_TemplateAssets[0].m_Id))
                        print(f"  Template 0 offset: {template_offset}")

                        # Check bytes between visual and template arrays
                        print(f"\nBytes between visual end (389) and template start ({template_offset}):")
                        gap = raw_data[389:template_offset]
                        print(f"  Gap size: {len(gap)} bytes")
                        print(f"  Gap hex: {' '.join(f'{b:02x}' for b in gap[:40])}")

                        # Try to find template array size field
                        print(f"\nLooking for template array size field...")
                        for check_offset in range(389, template_offset):
                            val = struct.unpack_from('<i', raw_data, check_offset)[0]
                            if val == 1:
                                print(f"  Found value '1' at offset {check_offset}")
                                # Check what's after
                                next_val = struct.unpack_from('<i', raw_data, check_offset + 4)[0]
                                print(f"    Next value: {next_val}")

                        return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    debug_arrays()
