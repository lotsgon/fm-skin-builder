#!/usr/bin/env python3
"""Debug script to analyze VTA binary structure."""

import struct
from pathlib import Path
import UnityPy

def hex_dump(data, offset, length=64):
    """Print hex dump of binary data."""
    for i in range(0, length, 16):
        addr = offset + i
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {addr:04x}: {hex_str:<48} {ascii_str}")

def analyze_element():
    """Analyze AboutClubCard element structure."""
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
                        print("Found AboutClubCard VTA")

                        # Get raw data
                        raw_data = obj.get_raw_data()
                        print(f"Raw data size: {len(raw_data)} bytes\n")

                        # Get elements for comparison
                        if hasattr(data, "m_VisualElementAssets"):
                            print(f"Visual elements: {len(data.m_VisualElementAssets)}")
                            for i, elem in enumerate(data.m_VisualElementAssets):
                                print(f"\nElement {i}:")
                                print(f"  m_Id: {elem.m_Id}")
                                print(f"  m_OrderInDocument: {elem.m_OrderInDocument}")
                                print(f"  m_ParentId: {elem.m_ParentId}")
                                print(f"  m_RuleIndex: {elem.m_RuleIndex}")
                                print(f"  m_Classes: {elem.m_Classes}")
                                print(f"  m_StylesheetPaths: {elem.m_StylesheetPaths}")
                                print(f"  m_Type: '{elem.m_Type}'" if hasattr(elem, 'm_Type') else "  m_Type: <not found>")
                                print(f"  m_Name: '{elem.m_Name}'" if hasattr(elem, 'm_Name') else "  m_Name: <not found>")

                        # Find first element offset
                        elem_id = 1426098328
                        id_bytes = struct.pack('<i', elem_id)
                        offset = raw_data.find(id_bytes)
                        print(f"\n\nFirst element at offset {offset}:")
                        print("="*60)
                        hex_dump(raw_data[offset:offset+128], offset, 128)

                        # Parse manually
                        print("\n\nManual parsing:")
                        print("="*60)
                        pos = offset
                        m_id = struct.unpack_from('<i', raw_data, pos)[0]
                        print(f"offset +0  (pos {pos}): m_Id = {m_id}")
                        pos += 4

                        m_order = struct.unpack_from('<i', raw_data, pos)[0]
                        print(f"offset +4  (pos {pos}): m_OrderInDocument = {m_order}")
                        pos += 4

                        m_parent = struct.unpack_from('<i', raw_data, pos)[0]
                        print(f"offset +8  (pos {pos}): m_ParentId = {m_parent}")
                        pos += 4

                        m_rule = struct.unpack_from('<I', raw_data, pos)[0]
                        print(f"offset +12 (pos {pos}): m_RuleIndex = {m_rule}")
                        pos += 4

                        print(f"\nUnknown bytes (20 bytes) at pos {pos}:")
                        unknown = raw_data[pos:pos+20]
                        hex_dump(unknown, pos, 20)
                        pos += 20

                        print(f"\nm_Classes array at pos {pos}:")
                        classes_count = struct.unpack_from('<i', raw_data, pos)[0]
                        print(f"  count = {classes_count}")
                        pos += 4

                        # m_StylesheetPaths
                        print(f"\nm_StylesheetPaths array at pos {pos}:")
                        paths_count = struct.unpack_from('<i', raw_data, pos)[0]
                        print(f"  count = {paths_count}")
                        pos += 4

                        print(f"\nNext 64 bytes at pos {pos}:")
                        hex_dump(raw_data[pos:pos+64], pos, 64)

                        return

            except Exception:
                pass

if __name__ == "__main__":
    analyze_element()
