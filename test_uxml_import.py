"""Test UXML importer with a real exported file."""

from src.utils.uxml_importer import UXMLImporter
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_simple_file():
    """Test importing a simple UXML file."""

    importer = UXMLImporter()

    # Use PlayerAttributesTile as test case
    test_file = "/workspaces/fm-skin-builder/exported_uxml_minimal/PlayerAttributesTile.uxml"

    print(f"Testing import of: {test_file}")
    print("=" * 60)

    try:
        result = importer.parse_uxml_file(test_file)

        print("\n✅ Import successful!")
        print(f"\nElements: {len(result['m_VisualElementAssets'])}")
        print(
            f"Bindings: {len(result['managedReferencesRegistry']['references'])}")

        # Show first few elements
        print("\n📋 First 5 elements:")
        for elem in result['m_VisualElementAssets'][:5]:
            print(
                f"  - {elem['m_Type']} (ID: {elem['m_Id']}, Parent: {elem['m_ParentId']})")

        # Show first few bindings
        print("\n🔗 First 5 bindings:")
        for binding in result['managedReferencesRegistry']['references'][:5]:
            binding_type = binding['type']['class']
            uxmlAssetId = binding['data']['uxmlAssetId']
            print(f"  - {binding_type} (Element ID: {uxmlAssetId})")

            # Show binding properties
            for key, value in binding['data'].items():
                if key != 'uxmlAssetId':
                    print(f"      {key}: {value}")

        # Validation report
        print("\n" + "=" * 60)
        print(importer.get_validation_report())

        # Save result for inspection
        output_file = "/tmp/imported_structure.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📁 Full structure saved to: {output_file}")

        return result

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        print("\n" + "=" * 60)
        print(importer.get_validation_report())
        raise


if __name__ == '__main__':
    test_import_simple_file()
