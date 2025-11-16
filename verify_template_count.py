#!/usr/bin/env python3
"""Verify template count location in header."""

from pathlib import Path
import struct
import UnityPy

def verify_counts():
    """Verify array count field locations."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    raw = obj.get_raw_data()

                    print("="*80)
                    print("ARRAY COUNT VERIFICATION")
                    print("="*80)
                    print()

                    visual_count = len(data.m_VisualElementAssets)
                    template_count = len(data.m_TemplateAssets)

                    print(f"Expected counts:")
                    print(f"  Visual elements: {visual_count}")
                    print(f"  Template assets: {template_count}")
                    print()

                    # Check offset 12
                    val_12 = struct.unpack_from('<i', raw, 12)[0]
                    print(f"Offset 12: value = {val_12}")
                    if val_12 == template_count:
                        print(f"  ✓ This matches template count!")
                    print()

                    # Check offset 152
                    val_152 = struct.unpack_from('<i', raw, 152)[0]
                    print(f"Offset 152: value = {val_152}")
                    if val_152 == visual_count:
                        print(f"  ✓ This matches visual count!")
                    print()

                    print("="*80)
                    print("COMPLETE STRUCTURE")
                    print("="*80)
                    print()
                    print("VTA binary layout:")
                    print(f"  Offset 0-11:    Header part 1")
                    print(f"  Offset 12:      Template assets count = {val_12}")
                    print(f"  Offset 16-151:  Header part 2")
                    print(f"  Offset 152:     Visual elements count = {val_152}")
                    print(f"  Offset 156-195: Visual elements type info")
                    print(f"  Offset 196-391: Visual elements data (2 elements)")
                    print(f"  Offset 392+:    Template assets data (1 element)")
                    print(f"                  (NO separate count field - uses offset 12)")
                    print()

                    print("CRITICAL INSIGHT:")
                    print("  Unity stores BOTH array counts in the header (before type info)")
                    print("  - Template count at offset 12")
                    print("  - Visual count at offset 152")
                    print("  - Arrays are stored sequentially without intermediate count fields")
                    print()

                    # Where does template type info go?
                    print("Question: Where is template assets type info?")
                    print()
                    print("Checking after visual elements (392+):")
                    # Template starts at 392 with element ID
                    # Check if there's type info before it
                    for off in range(392-40, 392, 4):
                        val = struct.unpack_from('<i', raw, off)[0]
                        print(f"  Offset {off}: {val}")
                    print()

                    print("Hypothesis: Template type info might be:")
                    print("  1. Not needed (same structure as visual elements)")
                    print("  2. Stored elsewhere in header")
                    print("  3. Stored inline with first template element")
                    print()

                    return

            except Exception as e:
                import traceback
                print(f"Error: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    verify_counts()
