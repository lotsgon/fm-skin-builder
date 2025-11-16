#!/usr/bin/env python3
"""Analyze the footer structure after template assets."""

import UnityPy
from pathlib import Path
import struct

def analyze_footer():
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                if obj.peek_name() == "AboutClubCard":
                    raw_data = obj.get_raw_data()
                    data = obj.read()

                    print("="*80)
                    print("FOOTER STRUCTURE ANALYSIS")
                    print("="*80)
                    print()

                    # Footer starts at offset 512
                    footer_offset = 512
                    footer_data = raw_data[footer_offset:]

                    print(f"Footer size: {len(footer_data)} bytes")
                    print(f"Footer starts at offset: {footer_offset}")
                    print()

                    # Print TypeTree fields that come after m_TemplateAssets
                    print("VTA fields AFTER m_TemplateAssets:")
                    if hasattr(data, "m_UxmlObjectEntries"):
                        print(f"  m_UxmlObjectEntries: {len(data.m_UxmlObjectEntries)} entries")
                        for i, entry in enumerate(data.m_UxmlObjectEntries):
                            print(f"    [{i}] {entry}")

                    if hasattr(data, "m_UxmlObjectIds"):
                        print(f"  m_UxmlObjectIds: {data.m_UxmlObjectIds}")

                    if hasattr(data, "m_AssetEntries"):
                        print(f"  m_AssetEntries: {len(data.m_AssetEntries)} entries")
                        for i, entry in enumerate(data.m_AssetEntries):
                            print(f"    [{i}] {entry}")

                    if hasattr(data, "m_Slots"):
                        print(f"  m_Slots: {len(data.m_Slots)} slots")
                        for i, slot in enumerate(data.m_Slots):
                            print(f"    [{i}] {slot}")

                    if hasattr(data, "m_ContentContainerId"):
                        print(f"  m_ContentContainerId: {data.m_ContentContainerId}")

                    if hasattr(data, "m_ContentHash"):
                        print(f"  m_ContentHash: {data.m_ContentHash}")

                    print()
                    print("="*80)
                    print("RAW FOOTER BYTES (first 200 bytes)")
                    print("="*80)
                    print()

                    # Print first 200 bytes of footer
                    for i in range(0, min(200, len(footer_data)), 16):
                        hex_str = ' '.join(f'{b:02x}' for b in footer_data[i:i+16])
                        offset = footer_offset + i
                        print(f"  {offset:04d}: {hex_str}")

                    print()
                    print("="*80)
                    print("INTERPRETING FOOTER AS ARRAY COUNTS/OFFSETS")
                    print("="*80)
                    print()

                    # Try to interpret as int32 values
                    for offset in range(footer_offset, min(footer_offset + 100, len(raw_data)), 4):
                        try:
                            val = struct.unpack_from('<i', raw_data, offset)[0]
                            # Show potentially interesting values
                            if -10 < val < 1000 or val < -1000000:
                                print(f"  Offset {offset}: {val:12d} (0x{val & 0xFFFFFFFF:08x})")
                        except:
                            pass

                    break
            except:
                pass

if __name__ == "__main__":
    analyze_footer()
