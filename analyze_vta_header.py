#!/usr/bin/env python3
"""Analyze VTA header structure before first element."""

from pathlib import Path
import struct
import UnityPy

def analyze_header():
    """Analyze the structure before the first element."""
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

                        print("=== VTA Header Analysis ===\n")
                        print(f"First element (ID {data.m_VisualElementAssets[0].m_Id}) starts at offset 196\n")

                        print("Hex dump of data before first element (offset 0-200):\n")
                        for i in range(0, 200, 16):
                            hex_str = ' '.join(f'{b:02x}' for b in raw_data[i:i+16])
                            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw_data[i:i+16])
                            print(f"  {i:04x}: {hex_str:<48} {ascii_str}")

                        print("\n\nInterpreting as int32 fields:\n")
                        for offset in range(0, 200, 4):
                            val = struct.unpack_from('<i', raw_data, offset)[0]
                            # Highlight interesting values
                            note = ""
                            if val == 2:
                                note = " ← Count of visual elements?"
                            elif val == 1:
                                note = " ← Count of template assets?"
                            elif val == 1426098328:  # First element ID
                                note = " ← First element ID!"
                            elif offset == 192:
                                note = " ← 4 bytes before first element"
                            elif offset == 152:
                                note = " ← Contains value 2 (from search)"

                            if note or val not in [0, -1] or offset % 16 == 0:
                                print(f"  offset {offset:3d}: {val:12d} (0x{val & 0xFFFFFFFF:08x}){note}")

                        return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    analyze_header()
