"""
Test VTA Round-Trip Serialization

Tests if we can:
1. Load a VTA
2. Parse all elements
3. Rebuild VTA binary
4. Compare to original
"""

import sys
import UnityPy
from pathlib import Path
from fm_skin_builder.core.uxml.vta_builder import VTABuilder
from fm_skin_builder.core.uxml.uxml_element_parser import parse_element_at_offset, find_element_offset


def test_roundtrip():
    """Test pure round-trip (no modifications)."""

    print("=" * 80)
    print("VTA Round-Trip Test")
    print("=" * 80)

    # Load test bundle
    bundle_path = 'test_bundles/ui-tiles_assets_all.bundle'
    target_vta = 'PlayerAttributesSmallBlock'

    print(f"\n1. Loading bundle: {bundle_path}")
    env = UnityPy.load(bundle_path)

    # Find target VTA
    original_raw = None
    visual_elements_orig = None
    template_elements_orig = None

    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour':
            try:
                data = obj.read()
                if hasattr(data, 'm_VisualElementAssets') and data.m_Name == target_vta:
                    print(f"   Found VTA: {data.m_Name}")
                    print(f"   Visual elements: {len(data.m_VisualElementAssets)}")
                    print(f"   Template assets: {len(data.m_TemplateAssets)}")

                    original_raw = obj.get_raw_data()
                    visual_elements_orig = list(data.m_VisualElementAssets)
                    template_elements_orig = list(data.m_TemplateAssets)

                    print(f"   Original size: {len(original_raw):,} bytes")
                    break
            except:
                continue

    if not original_raw:
        print(f"❌ Could not find VTA '{target_vta}'")
        return False

    # Parse elements from binary
    print(f"\n2. Parsing elements from binary...")

    visual_parsed = []
    for elem in visual_elements_orig:
        offset = find_element_offset(original_raw, elem.m_Id)
        if offset != -1:
            parsed = parse_element_at_offset(original_raw, offset)
            if parsed:
                visual_parsed.append(parsed)

    template_parsed = []
    for elem in template_elements_orig:
        offset = find_element_offset(original_raw, elem.m_Id)
        if offset != -1:
            parsed = parse_element_at_offset(original_raw, offset)
            if parsed:
                template_parsed.append(parsed)

    print(f"   Parsed {len(visual_parsed)} visual elements")
    print(f"   Parsed {len(template_parsed)} template elements")

    # Rebuild using VTABuilder
    print(f"\n3. Rebuilding VTA binary...")

    try:
        builder = VTABuilder(original_raw)
        rebuilt = builder.build(visual_parsed, template_parsed)

        print(f"   Rebuilt size: {len(rebuilt):,} bytes")

    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Compare
    print(f"\n4. Comparing original vs rebuilt...")

    if len(rebuilt) != len(original_raw):
        print(f"   ⚠️  Size mismatch: {len(rebuilt)} vs {len(original_raw)}")
        print(f"   Difference: {len(rebuilt) - len(original_raw):+,} bytes")

        # Find first difference
        min_len = min(len(rebuilt), len(original_raw))
        for i in range(min_len):
            if rebuilt[i] != original_raw[i]:
                print(f"   First difference at offset {i}")
                print(f"   Original: 0x{original_raw[i:i+16].hex()}")
                print(f"   Rebuilt:  0x{rebuilt[i:i+16].hex()}")
                break

        return False

    # Byte-for-byte comparison
    if rebuilt == original_raw:
        print("   ✅ PERFECT MATCH! Byte-for-byte identical!")
        return True
    else:
        # Find differences
        diffs = []
        for i in range(len(rebuilt)):
            if rebuilt[i] != original_raw[i]:
                diffs.append(i)
                if len(diffs) <= 10:
                    print(f"   Diff at offset {i}: {original_raw[i]:02x} → {rebuilt[i]:02x}")

        print(f"   ❌ Found {len(diffs)} byte differences")
        return False


if __name__ == '__main__':
    success = test_roundtrip()
    sys.exit(0 if success else 1)
