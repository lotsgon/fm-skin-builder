"""
Test binary UXML patching by extracting Unity's serialization format.
"""

from src.utils.uxml_importer import UXMLImporter
import sys
from pathlib import Path
import struct
import UnityPy

sys.path.insert(0, str(Path(__file__).parent))


def analyze_unity_serialization():
    """Analyze how Unity actually serializes UXML to understand the binary format."""

    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    print("Analyzing Unity UXML serialization format...")
    print("=" * 60)

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
            print(f"  Offset: {obj.byte_start}")
            print(f"  Size: {obj.byte_size} bytes")
            print(f"  PathID: {obj.path_id}")

            # Get the raw bytes
            with open(bundle_path, 'rb') as f:
                f.seek(obj.byte_start)
                raw_data = f.read(min(obj.byte_size, 512))  # First 512 bytes

            print(f"\n  First 256 bytes (hex):")
            for i in range(0, min(256, len(raw_data)), 16):
                hex_str = ' '.join(f'{b:02x}' for b in raw_data[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b <
                                    127 else '.' for b in raw_data[i:i+16])
                print(f"    {i:04x}: {hex_str:<48} {ascii_str}")

            # Try to identify structure
            print(f"\n  Element analysis:")
            print(
                f"    m_VisualElementAssets count: {len(data.m_VisualElementAssets)}")

            if len(data.m_VisualElementAssets) > 0:
                elem = data.m_VisualElementAssets[0]
                print(f"\n    First element:")
                print(f"      m_Id: {elem.m_Id}")
                print(f"      m_OrderInDocument: {elem.m_OrderInDocument}")
                print(f"      m_ParentId: {elem.m_ParentId}")
                print(f"      m_RuleIndex: {elem.m_RuleIndex}")
                print(f"      m_Type: {getattr(elem, 'm_Type', 'N/A')}")
                print(f"      m_Name: '{elem.m_Name}'")
                print(f"      m_Classes: {elem.m_Classes}")

                # Look for these values in the raw bytes
                print(
                    f"\n    Searching for m_Id ({elem.m_Id}) in raw bytes...")
                id_bytes = struct.pack('<i', elem.m_Id)
                id_offset = raw_data.find(id_bytes)
                if id_offset != -1:
                    print(
                        f"      Found at offset: {id_offset} (0x{id_offset:04x})")

            # Check if we can get the TypeTree
            print(f"\n  TypeTree info:")
            if hasattr(obj, 'type_tree'):
                print(f"    Has type_tree: Yes")
                tree = obj.get_type_tree()
                if tree:
                    print(f"    Tree nodes: {len(tree.m_Nodes)}")
            else:
                print(f"    Has type_tree: No")

            # Check serialized_type
            if hasattr(obj, 'serialized_type'):
                print(f"    Has serialized_type: Yes")

            break

        except Exception as e:
            continue


def test_read_write_cycle():
    """Test reading and writing back the same data."""

    bundle_path = Path("bundles/ui-tiles_assets_all.bundle")
    output_path = Path("build/test_binary_readwrite.bundle")

    print("\n" + "=" * 60)
    print("Testing read-write cycle...")
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

            print(f"\n✓ Found asset: {data.m_Name}")
            print(f"  Current elements: {len(data.m_VisualElementAssets)}")

            # Don't modify anything, just try to save it back
            print(f"\n  Attempting to save without modifications...")

            try:
                obj.save_typetree(data)
                print(f"  ✓ Save successful (no changes)")

                # Now save the bundle
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(env.file.save())

                print(f"  ✓ Bundle saved to: {output_path}")
                print(f"  Original size: {bundle_path.stat().st_size:,} bytes")
                print(f"  New size: {output_path.stat().st_size:,} bytes")

                # Try to load it back
                print(f"\n  Verifying saved bundle...")
                env2 = UnityPy.load(str(output_path))
                found = False
                for obj2 in env2.objects:
                    if obj2.type.name == "MonoBehaviour":
                        data2 = obj2.read()
                        if hasattr(data2, 'm_Name') and data2.m_Name == "PlayerAttributesTile":
                            found = True
                            print(f"  ✓ Asset found in saved bundle")
                            print(
                                f"  ✓ Elements: {len(data2.m_VisualElementAssets)}")
                            break

                if not found:
                    print(f"  ✗ Asset not found in saved bundle")

            except Exception as e:
                print(f"  ✗ Save failed: {e}")
                import traceback
                traceback.print_exc()

            break

        except Exception as e:
            continue


if __name__ == '__main__':
    analyze_unity_serialization()
    test_read_write_cycle()
