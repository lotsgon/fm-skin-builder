"""
Use UnityPy's get_raw_data/set_raw_data to bypass typetree serialization.
"""

from src.utils.uxml_importer import UXMLImporter
import sys
from pathlib import Path
import struct
import UnityPy

sys.path.insert(0, str(Path(__file__).parent))


def test_raw_data_access():
    """Test using get_raw_data and set_raw_data."""

    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    output_path = Path("build/test_raw_data_patch.bundle")

    print("Testing raw data access...")
    print("=" * 60)

    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue

        try:
            data = obj.read()

            if not hasattr(data, 'm_Name') or data.m_Name != "PlayerAttributesTile":
                continue

            if not hasattr(data, 'm_VisualElementAssets'):
                continue

            print(f"\n✓ Found: {data.m_Name}")
            print(f"  Elements: {len(data.m_VisualElementAssets)}")

            # Get the raw binary data
            print(f"\n  Getting raw data...")
            raw_data = obj.get_raw_data()

            print(f"  ✓ Raw data size: {len(raw_data)} bytes")
            print(f"  First 64 bytes (hex): {raw_data[:64].hex()}")

            # Get first element ID
            elem = data.m_VisualElementAssets[0]
            old_id = elem.m_Id
            new_id = old_id + 9999  # Large change for easy verification

            print(f"\n  First element m_Id: {old_id}")
            print(f"  Target new ID: {new_id}")

            # Search for the ID in raw data
            id_bytes = struct.pack('<i', old_id)
            offset = raw_data.find(id_bytes)

            if offset != -1:
                print(f"  ✓ Found ID at offset {offset} in raw data")

                # Check if it looks like the element structure
                if offset + 16 <= len(raw_data):
                    order = struct.unpack('<i', raw_data[offset+4:offset+8])[0]
                    parent = struct.unpack(
                        '<i', raw_data[offset+8:offset+12])[0]
                    rule = struct.unpack(
                        '<i', raw_data[offset+12:offset+16])[0]

                    print(f"  Structure check:")
                    print(
                        f"    m_OrderInDocument: {order} (expected: {elem.m_OrderInDocument})")
                    print(
                        f"    m_ParentId: {parent} (expected: {elem.m_ParentId})")
                    print(
                        f"    m_RuleIndex: {rule} (expected: {elem.m_RuleIndex})")

                    # RuleIndex might be -1 in Python but 0xFFFFFFFF in binary
                    matches = (order == elem.m_OrderInDocument and
                               parent == elem.m_ParentId)

                    if matches:
                        print(f"  ✓ Structure matches!")

                        # Patch the raw data
                        print(f"\n  Patching raw data...")
                        raw_data_mod = bytearray(raw_data)
                        struct.pack_into('<i', raw_data_mod, offset, new_id)

                        # Set it back
                        print(f"  Setting modified raw data...")
                        obj.set_raw_data(bytes(raw_data_mod))

                        # Save the bundle
                        print(f"  Saving bundle...")
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(env.file.save())

                        print(f"  ✓ Saved to: {output_path}")

                        # Verify
                        print(f"\n  Verifying...")
                        env2 = UnityPy.load(str(output_path))

                        for obj2 in env2.objects:
                            if obj2.type.name == "MonoBehaviour":
                                try:
                                    data2 = obj2.read()
                                    if hasattr(data2, 'm_Name') and data2.m_Name == "PlayerAttributesTile":
                                        elem2 = data2.m_VisualElementAssets[0]
                                        print(f"    Original ID: {old_id}")
                                        print(f"    Patched ID:  {elem2.m_Id}")

                                        if elem2.m_Id == new_id:
                                            print(
                                                f"\n  ✅ SUCCESS! Raw data patching works!")
                                            print(
                                                f"  This is the solution for UXML import!")
                                            return True
                                        else:
                                            print(
                                                f"  ✗ ID didn't change as expected")
                                        break
                                except Exception as e:
                                    pass
                    else:
                        print(f"  ✗ Structure doesn't match")
            else:
                print(f"  ✗ ID not found in raw data")

                # Try to understand the format
                print(f"\n  Analyzing raw data format...")
                print(f"  Looking for any of the first 5 element IDs...")

                for i, elem in enumerate(data.m_VisualElementAssets[:5]):
                    id_bytes = struct.pack('<i', elem.m_Id)
                    offset = raw_data.find(id_bytes)
                    if offset != -1:
                        print(
                            f"    Element [{i}] ID {elem.m_Id} found at offset {offset}")

            break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    return False


if __name__ == '__main__':
    success = test_raw_data_access()
    if success:
        print(f"\n" + "=" * 60)
        print("BREAKTHROUGH: We can modify UXML by:")
        print("1. Load bundle with UnityPy")
        print("2. Find the UXML asset")
        print("3. Get raw binary data with get_raw_data()")
        print("4. Patch specific bytes")
        print("5. Set back with set_raw_data()")
        print("6. Save bundle with env.file.save()")
        print("=" * 60)
