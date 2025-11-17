"""
Comprehensive VTA Round-Trip Test

This test verifies our complete understanding of the VTA format by:
1. Loading a VTA from a Unity bundle
2. Parsing ALL elements using our parser
3. Rebuilding the VTA using our builder
4. Comparing byte-for-byte with the original

SUCCESS = Byte-perfect match, proving our format understanding is complete
"""

import UnityPy
from fm_skin_builder.core.uxml.vta_builder import VTABuilder
from fm_skin_builder.core.uxml.uxml_element_parser import (
    find_element_offset,
    parse_element_at_offset,
)


def test_vta_roundtrip(bundle_path: str, vta_name: str):
    """
    Test full VTA round-trip for a specific VTA.

    Args:
        bundle_path: Path to Unity bundle
        vta_name: Name of VTA to test
    """
    print("=" * 100)
    print(f"VTA Round-Trip Test: {vta_name}")
    print("=" * 100)

    # Step 1: Load original VTA
    print("\n[1/5] Loading original VTA from bundle...")
    env = UnityPy.load(bundle_path)

    original_raw = None
    visual_elements_unity = None
    template_elements_unity = None

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_VisualElementAssets") and data.m_Name == vta_name:
                    original_raw = bytes(obj.get_raw_data())
                    visual_elements_unity = list(data.m_VisualElementAssets)
                    template_elements_unity = list(data.m_TemplateAssets)
                    print(f"   ✅ Found VTA: {len(original_raw):,} bytes")
                    print(
                        f"   Elements: {len(visual_elements_unity)} visual, {len(template_elements_unity)} template"
                    )
                    break
            except Exception:
                continue

    if not original_raw:
        print(f"   ❌ Could not find VTA '{vta_name}' in bundle")
        return False

    # Step 2: Parse all elements using our parser
    print("\n[2/5] Parsing all elements with our parser...")

    visual_parsed = []
    visual_failed = 0

    for idx, elem in enumerate(visual_elements_unity):
        offset = find_element_offset(original_raw, elem.m_Id)
        if offset != -1:
            parsed = parse_element_at_offset(original_raw, offset, debug=False)
            if parsed:
                visual_parsed.append(parsed)
            else:
                visual_failed += 1
                print(f"   ⚠️  Visual element {idx} failed to parse")
        else:
            visual_failed += 1
            print(f"   ⚠️  Visual element {idx} not found")

    template_parsed = []
    template_failed = 0

    for idx, elem in enumerate(template_elements_unity):
        offset = find_element_offset(original_raw, elem.m_Id)
        if offset != -1:
            parsed = parse_element_at_offset(original_raw, offset, debug=False)
            if parsed:
                template_parsed.append(parsed)
            else:
                template_failed += 1
                print(f"   ⚠️  Template element {idx} failed to parse")
        else:
            template_failed += 1
            print(f"   ⚠️  Template element {idx} not found")

    print(f"   Visual: {len(visual_parsed)}/{len(visual_elements_unity)} parsed")
    print(f"   Template: {len(template_parsed)}/{len(template_elements_unity)} parsed")

    if visual_failed > 0 or template_failed > 0:
        print(f"   ❌ Parsing failed for {visual_failed + template_failed} elements")
        return False

    print("   ✅ All elements parsed successfully!")

    # Step 3: Rebuild VTA using our builder
    print("\n[3/5] Rebuilding VTA binary...")

    try:
        builder = VTABuilder(original_raw)
        rebuilt_raw = builder.build(visual_parsed, template_parsed)
        print(f"   ✅ Rebuilt: {len(rebuilt_raw):,} bytes")
    except Exception as e:
        print(f"   ❌ Build failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 4: Compare sizes
    print("\n[4/5] Comparing sizes...")
    print(f"   Original: {len(original_raw):,} bytes")
    print(f"   Rebuilt:  {len(rebuilt_raw):,} bytes")

    if len(rebuilt_raw) != len(original_raw):
        diff = len(rebuilt_raw) - len(original_raw)
        print(f"   ❌ Size mismatch: {diff:+,} bytes")
        return False

    print("   ✅ Sizes match!")

    # Step 5: Byte-for-byte comparison
    print("\n[5/5] Byte-for-byte comparison...")

    if rebuilt_raw == original_raw:
        print("   🎉 PERFECT MATCH! Byte-for-byte identical!")
        print("\n" + "=" * 100)
        print("SUCCESS: Round-trip test passed!")
        print("=" * 100)
        return True
    else:
        # Find first difference
        for i in range(len(rebuilt_raw)):
            if rebuilt_raw[i] != original_raw[i]:
                print(f"   ❌ First difference at offset {i}:")
                print(f"      Original: {original_raw[i:i+16].hex()}")
                print(f"      Rebuilt:  {rebuilt_raw[i:i+16].hex()}")

                # Show some context
                start = max(0, i - 32)
                print(f"\n   Context (offset {start}-{i+32}):")
                print(f"      Original: {original_raw[start:i+32].hex()}")
                print(f"      Rebuilt:  {rebuilt_raw[start:i+32].hex()}")
                break

        print("\n" + "=" * 100)
        print("FAILED: Round-trip produced different output")
        print("=" * 100)
        return False


if __name__ == "__main__":
    # Test on a simple VTA first
    success = test_vta_roundtrip(
        "test_bundles/ui-tiles_assets_all.bundle", "ClubsStadiumsTile_2x2_Row"
    )

    if success:
        print("\n\n")
        # Test on a more complex VTA
        test_vta_roundtrip(
            "test_bundles/ui-tiles_assets_all.bundle", "StaffAdviceAndReportsCell"
        )
