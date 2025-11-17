#!/usr/bin/env python3
"""Locate m_VisualElementAssets and m_TemplateAssets array markers in binary."""

from pathlib import Path
import struct
import UnityPy

def locate_arrays():
    """Locate the two separate arrays in VTA binary data."""
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
                        print("=== Array Location Analysis ===\n")

                        print("UnityPy reports:")
                        print(f"  m_VisualElementAssets: {len(data.m_VisualElementAssets)} elements")
                        for elem in data.m_VisualElementAssets:
                            print(f"    - ID {elem.m_Id}")

                        print(f"  m_TemplateAssets: {len(data.m_TemplateAssets)} elements")
                        for elem in data.m_TemplateAssets:
                            print(f"    - ID {elem.m_Id}")

                        # Get raw data
                        raw_data = obj.get_raw_data()
                        print(f"\nRaw data size: {len(raw_data)} bytes\n")

                        # Search for count markers
                        print("Searching for array size markers (value 2 and value 1):\n")

                        # Look for the value 2 (VisualElements count)
                        visual_count = 2
                        visual_count_bytes = struct.pack('<i', visual_count)

                        offset = 0
                        visual_offsets = []
                        while True:
                            offset = raw_data.find(visual_count_bytes, offset)
                            if offset == -1:
                                break
                            visual_offsets.append(offset)
                            offset += 4

                        print(f"Found value '2' at offsets: {visual_offsets[:10]}")

                        # Look for the value 1 (TemplateAssets count)
                        template_count = 1
                        template_count_bytes = struct.pack('<i', template_count)

                        offset = 0
                        template_offsets = []
                        while True:
                            offset = raw_data.find(template_count_bytes, offset)
                            if offset == -1:
                                break
                            template_offsets.append(offset)
                            offset += 4

                        print(f"Found value '1' at offsets: {template_offsets[:15]}\n")

                        # We know element 0 starts at 196
                        # So visual elements array should have size field at 192
                        print("Expected locations:")
                        print("  m_VisualElementAssets count at: 192 (value should be 2)")
                        print("  First visual element at: 196")

                        # Verify
                        val_at_192 = struct.unpack_from('<i', raw_data, 192)[0]
                        print(f"  → Actual value at 192: {val_at_192}")

                        # Element 1 ends around 389, element 2 starts at 392
                        # Template array size should be somewhere around 389
                        print("\n  Checking around offset 389 (after visual elements)...")
                        for check_offset in range(385, 395):
                            val = struct.unpack_from('<i', raw_data, check_offset)[0]
                            if val == 1:
                                print(f"  → Found value '1' at offset {check_offset}")

                        # Check what's at specific offsets around the gap
                        print("\n  Bytes around gap (offset 385-400):")
                        gap_bytes = raw_data[385:400]
                        for i in range(0, len(gap_bytes), 4):
                            if i + 4 <= len(gap_bytes):
                                val = struct.unpack('<i', gap_bytes[i:i+4])[0]
                                actual_offset = 385 + i
                                print(f"    offset {actual_offset}: {val}")

                        return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    locate_arrays()
