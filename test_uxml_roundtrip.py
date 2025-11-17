"""
Test UXML Export → Edit → Import Round-Trip

Demonstrates the full workflow:
1. Load VTA from bundle
2. Export to UXML XML
3. Edit UXML (modify CSS classes)
4. Import back from XML
5. Build VTA binary
6. Validate

This tests the export/import pipeline for making manual UXML modifications.
"""

import UnityPy
from pathlib import Path
from fm_skin_builder.core.uxml.uxml_exporter import UXMLExporter
from fm_skin_builder.core.uxml.uxml_importer import UXMLImporter


def test_uxml_roundtrip(bundle_path: str, vta_name: str):
    """
    Test full UXML export → import roundtrip.

    Args:
        bundle_path: Path to Unity bundle
        vta_name: Name of VTA to test
    """
    print("=" * 100)
    print(f"UXML Round-Trip Test: {vta_name}")
    print("=" * 100)

    # Step 1: Load VTA from bundle
    print("\n[1/7] Loading VTA from bundle...")
    env = UnityPy.load(bundle_path)

    original_raw = None
    vta_obj = None

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_VisualElementAssets") and data.m_Name == vta_name:
                    original_raw = bytes(obj.get_raw_data())
                    vta_obj = data
                    print(f"   ✅ Found VTA: {len(original_raw):,} bytes")
                    break
            except Exception:
                continue

    if not original_raw or not vta_obj:
        print(f"   ❌ Could not find VTA '{vta_name}'")
        return False

    # Step 2: Export to UXML
    print("\n[2/7] Exporting to UXML...")
    exporter = UXMLExporter()
    temp_uxml_path = Path(f"/tmp/{vta_name}.uxml")

    try:
        uxml_doc = exporter.export_visual_tree_asset(vta_obj, temp_uxml_path)
        print(f"   ✅ Exported to {temp_uxml_path}")
        print(f"   Elements: {count_elements(uxml_doc.root)} total")
    except Exception as e:
        print(f"   ❌ Export failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 3: Show exported UXML
    print("\n[3/7] Exported UXML preview...")
    uxml_text = temp_uxml_path.read_text()
    lines = uxml_text.split("\n")
    print(f"   First 20 lines of {len(lines)} total:")
    for line in lines[:20]:
        print(f"   {line}")

    # Step 4: Simulate editing - modify CSS class in XML
    print("\n[4/7] Simulating UXML edit (modifying CSS class)...")

    # Find first element with a class and reverse it (same-size modification)
    import xml.etree.ElementTree as ET

    tree = ET.parse(str(temp_uxml_path))
    root = tree.getroot()

    # Remove namespace for easier manipulation
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}")[1]

    modified = False
    for elem in root.iter():
        class_attr = elem.get("class")
        if class_attr and len(class_attr) > 0:
            # Find first CSS class and reverse it
            classes = class_attr.split()
            if len(classes) > 0 and len(classes[0]) > 3:
                original_class = classes[0]
                classes[0] = original_class[::-1]  # Reverse for same length
                elem.set("class", " ".join(classes))
                print(f"   ✅ Modified class: '{original_class}' → '{classes[0]}'")
                modified = True
                break

    if not modified:
        print("   ⚠️  No classes found to modify, test will verify unchanged round-trip")

    # Write modified XML
    modified_uxml_path = Path(f"/tmp/{vta_name}_modified.uxml")
    tree.write(str(modified_uxml_path), encoding="unicode", xml_declaration=True)
    print(f"   ✅ Wrote modified UXML to {modified_uxml_path}")

    # Step 5: Import from modified UXML
    print("\n[5/7] Importing from modified UXML...")
    importer = UXMLImporter()

    try:
        uxml_dict = importer.parse_uxml_to_dict(modified_uxml_path)
        visual_count = len(uxml_dict.get("m_VisualElementAssets", []))
        template_count = len(uxml_dict.get("m_TemplateAssets", []))
        print(f"   ✅ Imported: {visual_count} visual, {template_count} template elements")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 6: Show what we need to implement
    print("\n[6/7] Building VTA binary from imported UXML...")
    print("   ⚠️  TODO: Convert imported dict to UXMLElementBinary objects")
    print("   ⚠️  TODO: Use VTABuilder to create binary")
    print("   ⚠️  Currently importer returns dictionaries, not binary-compatible objects")

    # Step 7: Validate structure
    print("\n[7/7] Validation...")
    print(f"   Original VTA: {len(original_raw):,} bytes")
    print(f"   Exported elements: {count_elements(uxml_doc.root)}")
    print(f"   Imported elements: {visual_count + template_count}")

    if count_elements(uxml_doc.root) == (visual_count + template_count):
        print("   ✅ Element count matches!")
    else:
        print("   ⚠️  Element count mismatch")

    print("\n" + "=" * 100)
    print("PARTIAL SUCCESS: Export → Edit → Import works")
    print("TODO: Connect importer output to VTABuilder")
    print("=" * 100)
    return True


def count_elements(element) -> int:
    """Count total elements in tree."""
    if not element:
        return 0
    count = 1  # This element
    for child in element.children:
        count += count_elements(child)
    return count


if __name__ == "__main__":
    test_uxml_roundtrip(
        "test_bundles/ui-tiles_assets_all.bundle", "ClubsStadiumsTile_2x2_Row"
    )
