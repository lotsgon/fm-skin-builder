#!/usr/bin/env python3
"""Deep analysis of unknown_field_4 to understand its role in hierarchy."""

from pathlib import Path
import struct
import UnityPy

def analyze_field_4():
    """Analyze unknown_field_4 across different elements and VTAs."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    print("=== Analysis of unknown_field_4 (Hierarchy Indicator?) ===\n")

    vta_count = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    vta_count += 1
                    asset_name = getattr(data, "m_Name", f"VTA_{obj.path_id}")

                    # Only analyze a few VTAs to find patterns
                    if vta_count > 5:
                        break

                    all_elements = []
                    if hasattr(data, "m_VisualElementAssets"):
                        all_elements.extend([(elem, "Visual") for elem in data.m_VisualElementAssets])
                    if hasattr(data, "m_TemplateAssets"):
                        all_elements.extend([(elem, "Template") for elem in data.m_TemplateAssets])

                    if len(all_elements) == 0:
                        continue

                    print(f"\n{'='*70}")
                    print(f"VTA: {asset_name}")
                    print(f"  Visual elements: {len([e for e in all_elements if e[1] == 'Visual'])}")
                    print(f"  Template assets: {len([e for e in all_elements if e[1] == 'Template'])}")
                    print(f"{'='*70}")

                    raw_data = obj.get_raw_data()

                    # Build hierarchy tree
                    elements_by_id = {}
                    for elem, elem_type in all_elements:
                        elements_by_id[elem.m_Id] = {
                            'elem': elem,
                            'type': elem_type,
                            'children': []
                        }

                    # Build parent-child relationships
                    root_elements = []
                    for elem, elem_type in all_elements:
                        if elem.m_ParentId == 0:
                            root_elements.append(elem.m_Id)
                        else:
                            if elem.m_ParentId in elements_by_id:
                                elements_by_id[elem.m_ParentId]['children'].append(elem.m_Id)

                    # Analyze each element
                    for elem, elem_type in all_elements:
                        # Find in binary to get unknown_field_4
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

                        # Read serialization fields
                        unknown_field_3 = struct.unpack_from('<i', raw_data, pos)[0]
                        m_serialized_data = struct.unpack_from('<i', raw_data, pos + 4)[0]
                        unknown_field_4 = struct.unpack_from('<i', raw_data, pos + 8)[0]
                        unknown_field_5 = struct.unpack_from('<i', raw_data, pos + 12)[0]

                        # Calculate hierarchy depth
                        depth = 0
                        parent_id = elem.m_ParentId
                        while parent_id != 0 and parent_id in elements_by_id:
                            depth += 1
                            parent_id = elements_by_id[parent_id]['elem'].m_ParentId
                            if depth > 10:  # Safety check
                                break

                        # Check if it's a root element
                        is_root = elem.m_ParentId == 0
                        has_children = len(elements_by_id[elem.m_Id]['children']) > 0

                        print(f"\n  [{elem_type:8}] ID={elem.m_Id:12} Order={elem.m_OrderInDocument:2}")
                        print(f"    Parent: {elem.m_ParentId:12} | Depth: {depth} | Root: {is_root} | Children: {len(elements_by_id[elem.m_Id]['children'])}")
                        print(f"    unknown_field_3: {unknown_field_3:5}")
                        print(f"    m_SerializedData: {m_serialized_data:5}")
                        print(f"    unknown_field_4: {unknown_field_4:5} ← ANALYZING THIS")
                        print(f"    unknown_field_5: {unknown_field_5:5}")

                        # Try to find correlation
                        if is_root and unknown_field_4 == -1:
                            print("    ✓ Pattern: Root element has unknown_field_4 = -1")
                        elif not is_root and unknown_field_4 == 0:
                            print("    ✓ Pattern: Non-root element has unknown_field_4 = 0")
                        else:
                            print("    ⚠ UNEXPECTED: Breaks pattern!")

            except Exception:
                pass

if __name__ == "__main__":
    analyze_field_4()
