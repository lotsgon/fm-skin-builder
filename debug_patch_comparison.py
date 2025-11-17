#!/usr/bin/env python3
"""Compare original and patched binary data to find corruption."""

from pathlib import Path
import struct
import UnityPy

def compare_binaries():
    """Compare original and patched AboutClubCard binary data."""
    original_bundle = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    patched_bundle = Path("test_output/ui-panelids-uxml_assets_all_v2.bundle")

    # Load original
    print("Loading ORIGINAL bundle...")
    orig_env = UnityPy.load(str(original_bundle))

    orig_raw = None
    for obj in orig_env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    orig_raw = obj.get_raw_data()
                    print(f"✓ Found original AboutClubCard: {len(orig_raw)} bytes")
                    break
            except:
                pass

    if not orig_raw:
        print("ERROR: Could not find original AboutClubCard")
        return

    # Load patched
    print("\nLoading PATCHED bundle...")
    patched_env = UnityPy.load(str(patched_bundle))

    patched_raw = None
    for obj in patched_env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    patched_raw = obj.get_raw_data()
                    print(f"✓ Found patched AboutClubCard: {len(patched_raw)} bytes")
                    break
            except Exception as e:
                # Try to get raw data even if read fails
                try:
                    patched_raw = obj.get_raw_data()
                    print(f"⚠ Found AboutClubCard but read() failed: {e}")
                    print(f"  Got raw data: {len(patched_raw)} bytes")
                    break
                except:
                    pass

    if not patched_raw:
        print("ERROR: Could not find patched AboutClubCard")
        return

    print(f"\n{'='*80}")
    print("SIZE COMPARISON")
    print(f"{'='*80}")
    print(f"Original: {len(orig_raw)} bytes")
    print(f"Patched:  {len(patched_raw)} bytes")
    print(f"Diff:     {len(patched_raw) - len(orig_raw):+d} bytes")

    # Compare headers
    print(f"\n{'='*80}")
    print("HEADER COMPARISON")
    print(f"{'='*80}")

    # Template count at offset 12
    orig_template_count = struct.unpack_from('<i', orig_raw, 12)[0]
    patch_template_count = struct.unpack_from('<i', patched_raw, 12)[0]
    print("\nOffset 12 (template count):")
    print(f"  Original: {orig_template_count}")
    print(f"  Patched:  {patch_template_count}")
    if orig_template_count != patch_template_count:
        print("  ⚠ CHANGED!")

    # Visual count at offset 152
    orig_visual_count = struct.unpack_from('<i', orig_raw, 152)[0]
    patch_visual_count = struct.unpack_from('<i', patched_raw, 152)[0]
    print("\nOffset 152 (visual count):")
    print(f"  Original: {orig_visual_count}")
    print(f"  Patched:  {patch_visual_count}")
    if orig_visual_count != patch_visual_count:
        print("  ⚠ CHANGED!")

    # Type info section (156-195)
    orig_typeinfo = orig_raw[156:196]
    patch_typeinfo = patched_raw[156:196]
    print("\nOffset 156-195 (type info):")
    if orig_typeinfo == patch_typeinfo:
        print("  ✓ Identical")
    else:
        print("  ⚠ CHANGED!")
        print(f"  Original: {orig_typeinfo.hex()[:60]}...")
        print(f"  Patched:  {patch_typeinfo.hex()[:60]}...")

    # First element (offset 196)
    print(f"\n{'='*80}")
    print("FIRST ELEMENT COMPARISON (offset 196)")
    print(f"{'='*80}")

    # Element ID
    orig_elem_id = struct.unpack_from('<i', orig_raw, 196)[0]
    patch_elem_id = struct.unpack_from('<i', patched_raw, 196)[0]
    print("\nElement ID at offset 196:")
    print(f"  Original: {orig_elem_id}")
    print(f"  Patched:  {patch_elem_id}")

    # Compare first 100 bytes of first element
    print("\nFirst 100 bytes of first element:")
    orig_elem_data = orig_raw[196:296]
    patch_elem_data = patched_raw[196:296]

    if orig_elem_data == patch_elem_data:
        print("  ✓ Identical")
    else:
        print("  ⚠ Different - showing hex comparison:")
        for i in range(0, min(100, len(orig_elem_data), len(patch_elem_data)), 16):
            orig_hex = ' '.join(f'{b:02x}' for b in orig_elem_data[i:i+16])
            patch_hex = ' '.join(f'{b:02x}' for b in patch_elem_data[i:i+16])
            marker = "  " if orig_elem_data[i:i+16] == patch_elem_data[i:i+16] else "⚠ "
            print(f"  {marker}{196+i:04x}: orig  {orig_hex}")
            print(f"  {marker}      patch {patch_hex}")

    # Find where they diverge
    print(f"\n{'='*80}")
    print("FINDING FIRST DIFFERENCE")
    print(f"{'='*80}")

    min_len = min(len(orig_raw), len(patched_raw))
    first_diff = None
    for i in range(min_len):
        if orig_raw[i] != patched_raw[i]:
            first_diff = i
            break

    if first_diff is None:
        if len(orig_raw) != len(patched_raw):
            print(f"Files are identical up to byte {min_len}, but different sizes")
        else:
            print("Files are identical!")
    else:
        print(f"\nFirst difference at offset {first_diff}:")
        start = max(0, first_diff - 16)
        end = min(len(orig_raw), len(patched_raw), first_diff + 32)

        print(f"\nOriginal around offset {first_diff}:")
        for i in range(start, end, 16):
            hex_str = ' '.join(f'{b:02x}' for b in orig_raw[i:i+16])
            marker = ">>>" if i <= first_diff < i+16 else "   "
            print(f"  {marker} {i:04x}: {hex_str}")

        print(f"\nPatched around offset {first_diff}:")
        for i in range(start, end, 16):
            hex_str = ' '.join(f'{b:02x}' for b in patched_raw[i:i+16])
            marker = ">>>" if i <= first_diff < i+16 else "   "
            print(f"  {marker} {i:04x}: {hex_str}")

        # Try to interpret what field this is
        if first_diff < 196:
            print("\n  → Difference is in HEADER section")
        elif first_diff >= 196:
            print("\n  → Difference is in ELEMENT DATA section")

if __name__ == "__main__":
    compare_binaries()
