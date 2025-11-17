#!/usr/bin/env python3
"""Identify unknown fields by comparing UnityPy data with binary structure."""

from pathlib import Path
import struct
import UnityPy

def identify_fields():
    """Identify unknown fields in VTA element structure."""
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
                        print("=== AboutClubCard VTA Analysis ===\n")

                        # Get all visual elements
                        all_elements = []
                        if hasattr(data, "m_VisualElementAssets"):
                            all_elements.extend(list(data.m_VisualElementAssets))
                        if hasattr(data, "m_TemplateAssets"):
                            all_elements.extend(list(data.m_TemplateAssets))

                        # Analyze each element
                        raw_data = obj.get_raw_data()

                        for i, elem in enumerate(all_elements):
                            print(f"\n{'='*60}")
                            print(f"Element {i}: ID={elem.m_Id}")
                            print(f"{'='*60}")

                            # List all attributes
                            print("\nAll UnityPy attributes:")
                            for attr in dir(elem):
                                if not attr.startswith('_') and not callable(getattr(elem, attr)):
                                    try:
                                        val = getattr(elem, attr)
                                        if not isinstance(val, (list, dict)) or len(str(val)) < 100:
                                            print(f"  {attr}: {val}")
                                    except:
                                        pass

                            # Find in binary
                            elem_id_bytes = struct.pack('<i', elem.m_Id)
                            offset = raw_data.find(elem_id_bytes)

                            if offset == -1:
                                print("  ERROR: Could not find in binary!")
                                continue

                            print(f"\nBinary structure at offset {offset}:")

                            # Fixed fields
                            m_id = struct.unpack_from('<i', raw_data, offset)[0]
                            m_order = struct.unpack_from('<i', raw_data, offset + 4)[0]
                            m_parent = struct.unpack_from('<i', raw_data, offset + 8)[0]
                            m_rule = struct.unpack_from('<I', raw_data, offset + 12)[0]

                            print(f"  offset +0:  m_Id = {m_id}")
                            print(f"  offset +4:  m_OrderInDocument = {m_order}")
                            print(f"  offset +8:  m_ParentId = {m_parent}")
                            print(f"  offset +12: m_RuleIndex = {m_rule if m_rule != 0xFFFFFFFF else -1}")

                            # Unknown section (20 bytes at offset 16-35)
                            print("\n  Unknown section (offset +16 to +35, 20 bytes):")
                            unknown1 = raw_data[offset + 16:offset + 36]

                            # Try to interpret as different types
                            print(f"    As 5 int32s: {struct.unpack('<iiiii', unknown1)}")
                            print(f"    As 10 int16s: {struct.unpack('<10h', unknown1)}")
                            print(f"    As hex: {' '.join(f'{b:02x}' for b in unknown1)}")

                            # Read classes
                            pos = offset + 36
                            num_classes = struct.unpack_from('<i', raw_data, pos)[0]
                            print(f"\n  offset +36: m_Classes count = {num_classes}")

                            # Skip classes
                            pos += 4
                            for _ in range(num_classes):
                                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                                pos += 4 + str_len + 1  # length + string + null
                                # Align
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Paths
                            paths_offset = pos - offset
                            num_paths = struct.unpack_from('<i', raw_data, pos)[0]
                            print(f"  offset +{paths_offset}: m_StylesheetPaths count = {num_paths}")
                            pos += 4

                            # Skip paths
                            for _ in range(num_paths):
                                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                                pos += 4 + str_len + 1
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Unknown section 2 (16 bytes)
                            unknown2_offset = pos - offset
                            unknown2 = raw_data[pos:pos + 16]
                            print(f"\n  Unknown section 2 (offset +{unknown2_offset} to +{unknown2_offset+15}, 16 bytes):")
                            print(f"    As 4 int32s: {struct.unpack('<iiii', unknown2)}")
                            print(f"    As hex: {' '.join(f'{b:02x}' for b in unknown2)}")

                        return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    identify_fields()
