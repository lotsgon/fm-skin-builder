#!/usr/bin/env python3
"""Analyze the type info section (156-195) to understand its structure."""

import UnityPy
import struct

def analyze_typeinfo():
    # Load original
    orig_env = UnityPy.load('test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle')
    v3_env = UnityPy.load('test_output/ui-panelids-uxml_assets_all_v3.bundle')

    orig_raw = None
    v3_raw = None

    for obj in orig_env.objects:
        if obj.type.name == 'MonoBehaviour' and obj.peek_name() == 'AboutClubCard':
            orig_raw = obj.get_raw_data()
            break

    for obj in v3_env.objects:
        if obj.type.name == 'MonoBehaviour':
            try:
                if obj.peek_name() == 'AboutClubCard':
                    v3_raw = obj.get_raw_data()
                    break
            except:
                pass

    print("TYPE INFO SECTION (offset 156-195):")
    print("="*80)
    print()

    print("Original (working):")
    typeinfo_orig = orig_raw[156:196]
    for i in range(0, 40, 16):
        hex_str = ' '.join(f'{b:02x}' for b in typeinfo_orig[i:i+16])
        print(f"  {156+i:03d}: {hex_str}")

    print()
    print("V3 (broken):")
    typeinfo_v3 = v3_raw[156:196]
    for i in range(0, 40, 16):
        hex_str = ' '.join(f'{b:02x}' for b in typeinfo_v3[i:i+16])
        print(f"  {156+i:03d}: {hex_str}")

    print()
    if typeinfo_orig == typeinfo_v3:
        print("✅ Type info sections are IDENTICAL")
    else:
        print("❌ Type info sections are DIFFERENT")
        print()
        print("Differences:")
        for i in range(40):
            if typeinfo_orig[i] != typeinfo_v3[i]:
                print(f"  Offset {156+i}: {typeinfo_orig[i]:02x} → {typeinfo_v3[i]:02x}")

    # Try to decode the type info
    print()
    print("="*80)
    print("DECODING TYPE INFO:")
    print("="*80)
    print()

    print("Interpreting as int32 values:")
    for offset in range(156, 196, 4):
        val_orig = struct.unpack_from('<i', orig_raw, offset)[0]
        val_v3 = struct.unpack_from('<i', v3_raw, offset)[0]
        match = "✓" if val_orig == val_v3 else "✗"
        print(f"  {match} Offset {offset}: {val_orig:12d} {'=' if val_orig == val_v3 else '→'} {val_v3:12d}")

    # Check strings in type info
    print()
    print("Looking for embedded strings:")
    for offset in range(156, 196):
        if orig_raw[offset] >= 0x20 and orig_raw[offset] <= 0x7E:
            # Printable ASCII
            str_len = 0
            for i in range(offset, min(196, offset + 30)):
                if orig_raw[i] == 0:
                    break
                if orig_raw[i] < 0x20 or orig_raw[i] > 0x7E:
                    break
                str_len += 1

            if str_len > 3:
                string = orig_raw[offset:offset+str_len].decode('ascii')
                print(f"  Offset {offset}: \"{string}\"")

if __name__ == "__main__":
    analyze_typeinfo()
