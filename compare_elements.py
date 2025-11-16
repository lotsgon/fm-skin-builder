#!/usr/bin/env python3
"""Compare original and patched element serialization."""

from pathlib import Path
import struct
import UnityPy

from fm_skin_builder.core.uxml.uxml_element_parser import parse_element_at_offset, find_element_offset

def hex_dump(data, label, max_bytes=64):
    """Print hex dump."""
    print(f"\n{label} ({len(data)} bytes):")
    for i in range(0, min(len(data), max_bytes), 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        print(f"  {i:04x}: {hex_str}")

def compare():
    """Compare element -277358335 before and after patching."""
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
                        print("Found AboutClubCard in original bundle\n")

                        # Get raw data
                        raw_data = obj.get_raw_data()

                        # Find element -277358335
                        elem_id = -277358335
                        offset = find_element_offset(raw_data, elem_id)
                        print(f"Element {elem_id} at offset {offset}")

                        # Parse it
                        elem = parse_element_at_offset(raw_data, offset, debug=False)
                        if elem:
                            print(f"\nOriginal element:")
                            print(f"  m_Id: {elem.m_Id}")
                            print(f"  m_OrderInDocument: {elem.m_OrderInDocument}")
                            print(f"  m_ParentId: {elem.m_ParentId}")
                            print(f"  m_RuleIndex: {elem.m_RuleIndex}")
                            print(f"  m_Classes: {elem.m_Classes}")
                            print(f"  m_StylesheetPaths: {elem.m_StylesheetPaths}")
                            print(f"  m_Type: '{elem.m_Type}'")
                            print(f"  m_Name: '{elem.m_Name}'")
                            print(f"  Parsed size: from offset {elem.offset} to {elem.offset + len(elem)}")

                            # Get original bytes and size
                            original_size = len(elem)
                            original_bytes = raw_data[offset:offset+200]
                            hex_dump(original_bytes, "Original binary")

                            # Now modify and serialize
                            print(f"\n\nModifying classes:")
                            print(f"  Before: {elem.m_Classes}")
                            elem.m_Classes = ['base-template-grow', 'test-class-added']
                            print(f"  After: {elem.m_Classes}")

                            modified_bytes = elem.to_bytes()
                            modified_size = len(elem)  # Size after modification

                            hex_dump(modified_bytes, "Modified binary", max_bytes=200)

                            print(f"\n\nSize comparison:")
                            print(f"  Original: {original_size} bytes (calculated before modification)")
                            print(f"  Modified (__len__): {modified_size} bytes (calculated after modification)")
                            print(f"  Modified (actual): {len(modified_bytes)} bytes (serialized)")
                            print(f"  Difference: {len(modified_bytes) - original_size} bytes")

                        return

            except Exception as e:
                pass

if __name__ == "__main__":
    compare()
