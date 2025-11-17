#!/usr/bin/env python3
"""Analyze field patterns to identify unknown sections."""

from pathlib import Path
import struct
import UnityPy


def analyze_patterns():
    """Analyze patterns in unknown fields."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = hasattr(data, "m_VisualElementAssets") or hasattr(
                    data, "m_TemplateAssets"
                )

                if is_vta:
                    asset_name = getattr(data, "m_Name", "")
                    if asset_name == "AboutClubCard":
                        print("=== Field Mapping Analysis ===\n")

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

                            # Get UnityPy fields
                            print("\nUnityPy fields:")
                            print(f"  m_PickingMode: {elem.m_PickingMode}")
                            print(f"  m_SkipClone: {elem.m_SkipClone}")

                            # Check for m_SerializedData
                            if hasattr(elem, "m_SerializedData"):
                                serialized_data = elem.m_SerializedData
                                print(f"  m_SerializedData: {serialized_data}")
                                # Extract rid if it's in the string representation
                                sd_str = str(serialized_data)
                                if "rid=" in sd_str:
                                    rid = sd_str.split("rid=")[1].split(">")[0]
                                    print(f"    → rid value: {rid}")

                            # Find in binary
                            elem_id_bytes = struct.pack("<i", elem.m_Id)
                            offset = raw_data.find(elem_id_bytes)

                            if offset == -1:
                                continue

                            # Parse unknown section 1 (20 bytes at offset 16-35)
                            unknown1 = struct.unpack(
                                "<iiiii", raw_data[offset + 16 : offset + 36]
                            )
                            print("\nUnknown section 1 (20 bytes):")
                            print(f"  int[0]: {unknown1[0]} (likely m_PickingMode)")
                            print(f"  int[1]: {unknown1[1]} (likely m_SkipClone)")
                            print(
                                f"  int[2]: {unknown1[2]} (likely m_XmlNamespace ref)"
                            )
                            print(f"  int[3]: {unknown1[3]} (?)")
                            print(f"  int[4]: {unknown1[4]} (?)")

                            # Skip to unknown section 2
                            pos = offset + 36
                            # Skip m_Classes
                            num_classes = struct.unpack_from("<i", raw_data, pos)[0]
                            pos += 4
                            for _ in range(num_classes):
                                str_len = struct.unpack_from("<i", raw_data, pos)[0]
                                pos += 4 + str_len + 1
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Skip m_StylesheetPaths
                            num_paths = struct.unpack_from("<i", raw_data, pos)[0]
                            pos += 4
                            for _ in range(num_paths):
                                str_len = struct.unpack_from("<i", raw_data, pos)[0]
                                pos += 4 + str_len + 1
                                remainder = pos % 4
                                if remainder != 0:
                                    pos += 4 - remainder

                            # Unknown section 2 (16 bytes)
                            unknown2 = struct.unpack("<iiii", raw_data[pos : pos + 16])
                            print("\nUnknown section 2 (16 bytes):")
                            print(f"  int[0]: {unknown2[0]} (?)")
                            print(
                                f"  int[1]: {unknown2[1]} (likely m_SerializedData rid)"
                            )
                            print(f"  int[2]: {unknown2[2]} (?)")
                            print(f"  int[3]: {unknown2[3]} (?)")

                        return

            except Exception:
                pass


if __name__ == "__main__":
    analyze_patterns()
