#!/usr/bin/env python3
"""Try to identify remaining unknown fields by checking all UnityPy attributes."""

from pathlib import Path
import struct
import UnityPy

def identify_remaining():
    """Identify remaining unknown fields."""
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
                        print("=== Comprehensive UnityPy Attribute Analysis ===\n")

                        all_elements = []
                        if hasattr(data, "m_VisualElementAssets"):
                            all_elements.extend(list(data.m_VisualElementAssets))
                        if hasattr(data, "m_TemplateAssets"):
                            all_elements.extend(list(data.m_TemplateAssets))

                        raw_data = obj.get_raw_data()

                        for i, elem in enumerate(all_elements):
                            print(f"\n{'='*60}")
                            print(f"Element {i}: ID={elem.m_Id}")
                            print(f"{'='*60}")

                            # List ALL attributes with their values
                            print("\nAll attributes:")
                            attrs = {}
                            for attr in dir(elem):
                                if not attr.startswith('_') and not callable(getattr(elem, attr)):
                                    try:
                                        val = getattr(elem, attr)
                                        attrs[attr] = val
                                        # Only print non-empty/non-default values
                                        if val not in [None, [], '', 0, False] or attr in [
                                            'm_PickingMode', 'm_SkipClone', 'm_RuleIndex',
                                            'm_OrderInDocument', 'm_Id', 'm_ParentId'
                                        ]:
                                            print(f"  {attr}: {val}")
                                    except:
                                        pass

                            # Find in binary
                            elem_id_bytes = struct.pack('<i', elem.m_Id)
                            offset = raw_data.find(elem_id_bytes)

                            if offset == -1:
                                continue

                            # Skip to serialization section
                            pos = offset + 36
                            # Skip m_Classes
                            num_classes = struct.unpack_from('<i', raw_data, pos)[0]
                            pos += 4
                            for _ in range(num_classes):
                                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                                pos += 4 + str_len + 1
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Skip m_StylesheetPaths
                            num_paths = struct.unpack_from('<i', raw_data, pos)[0]
                            pos += 4
                            for _ in range(num_paths):
                                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                                pos += 4 + str_len + 1
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Serialization section (16 bytes)
                            ser_fields = struct.unpack('<iiii', raw_data[pos:pos + 16])
                            print("\nBinary serialization section:")
                            print(f"  Field[0]: {ser_fields[0]} (unknown_field_3, always 0)")
                            print(f"  Field[1]: {ser_fields[1]} (m_SerializedData rid)")
                            print(f"  Field[2]: {ser_fields[2]} (unknown_field_4, -1 or 0)")
                            print(f"  Field[3]: {ser_fields[3]} (unknown_field_5, always 0)")

                            # Check for any list/array attributes
                            print("\nArray/List attributes:")
                            for attr, val in attrs.items():
                                if isinstance(val, (list, tuple)) and len(val) > 0:
                                    print(f"  {attr}: {val[:3]}{'...' if len(val) > 3 else ''}")

                        return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    identify_remaining()
