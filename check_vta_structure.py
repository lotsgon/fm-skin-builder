#!/usr/bin/env python3
"""Check the VTA structure to understand how elements are stored."""

from pathlib import Path
import struct
import UnityPy

def check_structure():
    """Check AboutClubCard VTA structure."""
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
                        print("Found AboutClubCard VTA\n")

                        print(f"m_VisualElementAssets: {len(data.m_VisualElementAssets)} elements")
                        for i, elem in enumerate(data.m_VisualElementAssets):
                            print(f"  [{i}] ID={elem.m_Id}, Order={elem.m_OrderInDocument}")

                        print(f"\nm_TemplateAssets: {len(data.m_TemplateAssets)} elements")
                        for i, elem in enumerate(data.m_TemplateAssets):
                            print(f"  [{i}] ID={elem.m_Id}, Order={elem.m_OrderInDocument}")

                        # Check raw data
                        raw_data = obj.get_raw_data()
                        print(f"\n\nRaw data size: {len(raw_data)} bytes")

                        # Find array counts in binary
                        print("\nSearching for array size markers...")
                        for i in range(0, min(200, len(raw_data)), 4):
                            val = struct.unpack_from('<i', raw_data, i)[0]
                            if val == 2:  # Visual elements count
                                print(f"  Found '2' at offset {i}")
                            if val == 1:  # Template assets count
                                print(f"  Found '1' at offset {i}")
                            if val == 3:  # Total?
                                print(f"  Found '3' at offset {i}")

                        return

            except Exception as e:
                pass

if __name__ == "__main__":
    check_structure()
