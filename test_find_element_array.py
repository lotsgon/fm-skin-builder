"""
Find the element array by looking for sequences of element IDs.
"""

import sys
from pathlib import Path
import struct
import UnityPy

sys.path.insert(0, str(Path(__file__).parent))


def find_element_array():
    """Find where the element array is stored by looking for ID sequences."""

    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    bundle_data = bundle_path.read_bytes()

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

            print(f"Found: {data.m_Name}")
            print(
                f"Object range: {obj.byte_start} - {obj.byte_start + obj.byte_size}")
            print(f"Elements: {len(data.m_VisualElementAssets)}")
            print()

            # Get first 10 element IDs
            element_ids = [
                elem.m_Id for elem in data.m_VisualElementAssets[:10]]
            print(f"First 10 element IDs:")
            for i, eid in enumerate(element_ids):
                print(f"  [{i}] {eid:11d} (0x{eid & 0xFFFFFFFF:08x})")

            # Look for a sequence of these IDs in the bundle
            print(f"\nSearching for ID sequence in bundle...")

            # Try to find first 3 IDs in sequence
            id0_bytes = struct.pack('<i', element_ids[0])
            id1_bytes = struct.pack('<i', element_ids[1])
            id2_bytes = struct.pack('<i', element_ids[2])

            # Search for first ID
            offset = 0
            found_sequences = []

            while True:
                offset = bundle_data.find(id0_bytes, offset)
                if offset == -1:
                    break

                # Check if next IDs follow
                check_offset = offset + 4
                # Skip potential padding/other fields (try different strides)
                for stride in [4, 8, 12, 16, 20, 24, 28, 32, 36, 40]:
                    id1_offset = offset + stride
                    id2_offset = id1_offset + stride

                    if (id1_offset + 4 <= len(bundle_data) and
                            id2_offset + 4 <= len(bundle_data)):

                        found_id1 = struct.unpack(
                            '<i', bundle_data[id1_offset:id1_offset+4])[0]
                        found_id2 = struct.unpack(
                            '<i', bundle_data[id2_offset:id2_offset+4])[0]

                        if found_id1 == element_ids[1] and found_id2 == element_ids[2]:
                            found_sequences.append((offset, stride))
                            print(
                                f"  ✓ Found sequence at offset {offset}, stride {stride}")

                            # Show more context
                            print(f"    Bytes at offset:")
                            for i in range(min(5, len(element_ids))):
                                elem_offset = offset + (i * stride)
                                elem_bytes = bundle_data[elem_offset:elem_offset+stride]
                                elem_id = struct.unpack(
                                    '<i', elem_bytes[:4])[0]
                                print(
                                    f"      [{i}] offset {elem_offset:10d}: {elem_bytes.hex()[:32]}... (ID: {elem_id})")

                            break

                offset += 1

            if found_sequences:
                print(
                    f"\n✓ Found {len(found_sequences)} potential element array location(s)")

                # Use the first one that's likely correct
                array_offset, stride = found_sequences[0]

                print(f"\nUsing offset: {array_offset}, stride: {stride}")
                print(
                    f"This is {'INSIDE' if obj.byte_start <= array_offset < obj.byte_start + obj.byte_size else 'OUTSIDE'} the object range")

                # Now try to patch the first element
                print(f"\nAttempting to patch first element...")

                bundle_data_mod = bytearray(bundle_data)

                # Patch just the m_Id field
                old_id = element_ids[0]
                new_id = old_id + 1000  # Change significantly for easy verification

                struct.pack_into('<i', bundle_data_mod, array_offset, new_id)

                # Save
                output_path = Path("build/test_element_array_patch.bundle")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(bundle_data_mod)

                print(f"Saved patched bundle to: {output_path}")

                # Verify
                print(f"\nVerifying patch...")
                env2 = UnityPy.load(str(output_path))

                for obj2 in env2.objects:
                    if obj2.type.name == "MonoBehaviour":
                        try:
                            data2 = obj2.read()
                            if hasattr(data2, 'm_Name') and data2.m_Name == "PlayerAttributesTile":
                                elem2 = data2.m_VisualElementAssets[0]
                                print(f"  Original ID: {old_id}")
                                print(f"  New ID:      {elem2.m_Id}")

                                if elem2.m_Id == new_id:
                                    print(f"  ✅ SUCCESS! Binary patching works!")
                                    return True
                                else:
                                    print(f"  ✗ Patch didn't work")
                                break
                        except:
                            pass
            else:
                print(f"\n✗ Could not find element array")

            break

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    return False


if __name__ == '__main__':
    find_element_array()
