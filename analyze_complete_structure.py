#!/usr/bin/env python3
"""Complete VTA binary format analysis to understand exact structure."""

from pathlib import Path
import struct
import UnityPy

def analyze_complete_vta():
    """Analyze the complete VTA structure including all headers and arrays."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    raw = obj.get_raw_data()

                    print("="*80)
                    print("COMPLETE VTA BINARY STRUCTURE ANALYSIS")
                    print("="*80)
                    print()

                    print(f"VTA Name: {data.m_Name}")
                    print(f"Total size: {len(raw)} bytes")
                    print()

                    # Get UnityPy's parsed structure
                    print("UnityPy parsed structure:")
                    print(f"  m_VisualElementAssets: {len(data.m_VisualElementAssets)} elements")
                    for i, elem in enumerate(data.m_VisualElementAssets):
                        print(f"    [{i}] ID={elem.m_Id}, Order={elem.m_OrderInDocument}, Parent={elem.m_ParentId}")

                    print(f"  m_TemplateAssets: {len(data.m_TemplateAssets)} elements")
                    for i, elem in enumerate(data.m_TemplateAssets):
                        print(f"    [{i}] ID={elem.m_Id}, Order={elem.m_OrderInDocument}, Parent={elem.m_ParentId}")
                    print()

                    # Find element offsets
                    elem0_id = data.m_VisualElementAssets[0].m_Id
                    elem1_id = data.m_VisualElementAssets[1].m_Id
                    elem2_id = data.m_TemplateAssets[0].m_Id

                    elem0_offset = raw.find(struct.pack('<i', elem0_id))
                    elem1_offset = raw.find(struct.pack('<i', elem1_id))
                    elem2_offset = raw.find(struct.pack('<i', elem2_id))

                    print("Element locations in binary:")
                    print(f"  Visual Element 0 (ID {elem0_id}): offset {elem0_offset}")
                    print(f"  Visual Element 1 (ID {elem1_id}): offset {elem1_offset}")
                    print(f"  Template Asset 0 (ID {elem2_id}): offset {elem2_offset}")
                    print()

                    # Element sizes (from previous analysis)
                    elem0_size = 93 + 3  # 93 bytes + 3 padding
                    elem1_size = 97 + 3  # 97 bytes + 3 padding (before class added)

                    print("Calculated element boundaries:")
                    print(f"  Element 0: {elem0_offset} - {elem0_offset + elem0_size - 1}")
                    print(f"  Element 1: {elem1_offset} - {elem1_offset + elem1_size - 1}")
                    print(f"  Element 2: {elem2_offset} - ???")
                    print()

                    # Analyze header (0 - elem0_offset)
                    print("="*80)
                    print("HEADER ANALYSIS (0 to first element)")
                    print("="*80)
                    print()

                    print("Looking for array count fields:")
                    print()

                    # The value 2 (visual elements count)
                    visual_count_offset = None
                    for off in range(0, elem0_offset, 4):
                        val = struct.unpack_from('<i', raw, off)[0]
                        if val == 2:
                            print(f"  Found value 2 at offset {off}")
                            # Check surrounding context
                            if off >= 4:
                                prev = struct.unpack_from('<i', raw, off - 4)[0]
                                print(f"    Previous: {prev}")
                            if off + 4 < len(raw):
                                next_val = struct.unpack_from('<i', raw, off + 4)[0]
                                print(f"    Next: {next_val}")

                            # Likely candidate is at 152
                            if off == 152:
                                visual_count_offset = off
                                print(f"    → This is likely the visual elements count!")

                    print()

                    # The value 1 (template assets count)
                    template_count_offset = None
                    for off in range(0, elem0_offset, 4):
                        val = struct.unpack_from('<i', raw, off)[0]
                        if val == 1:
                            # Check if this could be template count
                            if off >= 4:
                                prev = struct.unpack_from('<i', raw, off - 4)[0]
                            else:
                                prev = None

                            if off + 4 < len(raw):
                                next_val = struct.unpack_from('<i', raw, off + 4)[0]
                            else:
                                next_val = None

                            # Skip if it's clearly not an array count (e.g., part of a string length)
                            # Array counts are usually followed by type info or element data
                            if off in [12, 16, 60]:  # From our earlier search
                                print(f"  Found value 1 at offset {off} (prev={prev}, next={next_val})")

                    print()
                    print("="*80)
                    print("STRUCTURE BREAKDOWN")
                    print("="*80)
                    print()

                    # Map out the structure
                    print("Based on analysis:")
                    print()
                    print(f"0-151:     VTA header/metadata ({152} bytes)")
                    print(f"152-155:   m_VisualElementAssets count = 2 (4 bytes)")
                    print(f"156-195:   Type info for VisualElementAssets ({elem0_offset - 156} bytes)")
                    print(f"196-{elem1_offset + elem1_size - 1}:   Visual elements array data")
                    print(f"  196-{elem0_offset + elem0_size - 1}:  Element 0 ({elem0_size} bytes with padding)")
                    print(f"  {elem1_offset}-{elem1_offset + elem1_size - 1}:  Element 1 ({elem1_size} bytes with padding)")
                    print()

                    # What comes after visual elements?
                    visual_end = elem1_offset + elem1_size
                    print(f"{visual_end}-{elem2_offset - 1}:   Gap/metadata before template assets ({elem2_offset - visual_end} bytes)")

                    # Analyze the gap
                    print()
                    print("Analyzing gap content:")
                    gap_data = raw[visual_end:elem2_offset]
                    print(f"  Gap size: {len(gap_data)} bytes")
                    print(f"  Gap hex: {' '.join(f'{b:02x}' for b in gap_data)}")

                    # Check for template count in the gap (should be somewhere in header actually)
                    print()
                    print("HYPOTHESIS:")
                    print("  Both array counts might be in the header (before offset 152)")
                    print("  Let me check offsets 12 and 16 more carefully:")
                    print()

                    val_12 = struct.unpack_from('<i', raw, 12)[0]
                    val_16 = struct.unpack_from('<i', raw, 16)[0]
                    print(f"  Offset 12: {val_12} (could be template count)")
                    print(f"  Offset 16: {val_16} (could be visual count? No, visual is 2)")
                    print()

                    # Check Unity's TypeTree structure
                    print("Unity typically stores arrays as:")
                    print("  - Array size (int32)")
                    print("  - Array data")
                    print()
                    print("For nested structures, it might be:")
                    print("  - Header with multiple counts")
                    print("  - Type info")
                    print("  - Array 1 data")
                    print("  - Array 2 data")
                    print()

                    return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    analyze_complete_vta()
