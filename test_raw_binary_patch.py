"""
Alternative approach: Use UnityPy's raw binary access and only modify specific bytes.
"""

import sys
from pathlib import Path
import struct
import UnityPy

sys.path.insert(0, str(Path(__file__).parent))


def test_raw_binary_access():
    """Test accessing and modifying raw binary data."""

    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    output_path = Path("build/test_raw_binary.bundle")

    print("Testing raw binary access...")
    print("=" * 60)

    # Load the entire bundle into memory
    bundle_data = bytearray(bundle_path.read_bytes())

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
            print(f"  Byte offset: {obj.byte_start}")
            print(f"  Byte size: {obj.byte_size}")
            print(f"  Elements: {len(data.m_VisualElementAssets)}")

            # Get the element we want to modify
            elem = data.m_VisualElementAssets[0]
            old_id = elem.m_Id
            new_id = old_id + 1  # Just increment by 1 for testing

            print(f"\n  First element m_Id: {old_id}")
            print(f"  Want to change to: {new_id}")

            # Search for the ID in the raw bundle data around the object
            search_start = obj.byte_start
            search_end = obj.byte_start + obj.byte_size

            id_bytes = struct.pack('<i', old_id)

            print(f"\n  Searching for ID bytes in object range...")
            print(f"  Looking for: {id_bytes.hex()}")

            # Search for ALL occurrences of the ID
            offsets = []
            start = 0
            while True:
                offset = bundle_data.find(id_bytes, start)
                if offset == -1:
                    break
                offsets.append(offset)
                start = offset + 1

            print(f"  Found {len(offsets)} occurrence(s) of ID in bundle:")
            for offset in offsets:
                in_range = search_start <= offset < search_end
                print(
                    f"    Offset: {offset:10d} {'[IN OBJECT RANGE]' if in_range else ''}")

            # Use the first occurrence
            if len(offsets) > 0:
                offset = offsets[0]
                print(
                    f"  ✓ Found at offset: {offset} (relative: {offset - search_start})")

                # Verify it's the right one by checking context
                # Read a few bytes before and after
                context_before = bundle_data[offset-8:offset]
                context_after = bundle_data[offset+4:offset+12]

                print(f"  Context before: {context_before.hex()}")
                print(
                    f"  ID bytes:       {bundle_data[offset:offset+4].hex()}")
                print(f"  Context after:  {context_after.hex()}")

                # Check if this looks like an element structure
                # Typically: m_Id (4), m_OrderInDocument (4), m_ParentId (4), m_RuleIndex (4)
                order = struct.unpack('<i', bundle_data[offset+4:offset+8])[0]
                parent = struct.unpack(
                    '<i', bundle_data[offset+8:offset+12])[0]
                rule = struct.unpack('<i', bundle_data[offset+12:offset+16])[0]

                print(f"\n  Interpreting as element structure:")
                print(f"    m_Id: {old_id}")
                print(
                    f"    m_OrderInDocument: {order} (expected: {elem.m_OrderInDocument})")
                print(
                    f"    m_ParentId: {parent} (expected: {elem.m_ParentId})")
                print(
                    f"    m_RuleIndex: {rule} (expected: {elem.m_RuleIndex})")

                if (order == elem.m_OrderInDocument and
                    parent == elem.m_ParentId and
                        rule == elem.m_RuleIndex):
                    print(f"  ✓ Structure matches! This is definitely the element.")

                    # Now patch it
                    print(f"\n  Patching m_Id from {old_id} to {new_id}...")
                    struct.pack_into('<i', bundle_data, offset, new_id)

                    # Save the modified bundle
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(bundle_data)

                    print(f"  ✓ Patched bundle saved to: {output_path}")

                    # Verify the patch worked
                    print(f"\n  Verifying patched bundle...")
                    env2 = UnityPy.load(str(output_path))

                    for obj2 in env2.objects:
                        if obj2.type.name == "MonoBehaviour":
                            try:
                                data2 = obj2.read()
                                if hasattr(data2, 'm_Name') and data2.m_Name == "PlayerAttributesTile":
                                    if hasattr(data2, 'm_VisualElementAssets'):
                                        elem2 = data2.m_VisualElementAssets[0]
                                        print(
                                            f"  Loaded element m_Id: {elem2.m_Id}")

                                        if elem2.m_Id == new_id:
                                            print(
                                                f"  ✅ SUCCESS! ID was successfully patched!")
                                        else:
                                            print(
                                                f"  ✗ ID is still {elem2.m_Id}, expected {new_id}")
                                        break
                            except:
                                pass
                else:
                    print(
                        f"  ✗ Structure doesn't match, might be a different occurrence")
            else:
                print(f"  ✗ ID not found in object range")

                # Try searching the entire bundle
                print(f"\n  Searching entire bundle...")
                offset = bundle_data.find(id_bytes)
                if offset != -1:
                    print(f"  Found at: {offset} (outside object range)")

            break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == '__main__':
    test_raw_binary_access()
