#!/usr/bin/env python3
"""Verify that the patched bundle contains the modified CSS class."""

from pathlib import Path
import UnityPy

def verify_patch():
    """Verify AboutClubCard was patched correctly."""
    bundle_path = Path("test_output/ui-panelids-uxml_assets_all.bundle")

    if not bundle_path.exists():
        print("ERROR: Output bundle not found!")
        return False

    print(f"Loading patched bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    print(f"Total objects in bundle: {len(list(env.objects))}")

    found_count = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or
                         hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    found_count += 1
                    asset_name = getattr(data, "m_Name", "")
                    if asset_name == "AboutClubCard":
                        print("\n✓ Found AboutClubCard VTA")

                        if hasattr(data, "m_VisualElementAssets"):
                            print(f"\nVisual elements: {len(data.m_VisualElementAssets)}")
                            for i, elem in enumerate(data.m_VisualElementAssets):
                                print(f"\nElement {i} (ID {elem.m_Id}):")
                                print(f"  Type: {elem.m_Type if hasattr(elem, 'm_Type') else 'N/A'}")
                                print(f"  Classes: {elem.m_Classes}")

                                # Check for our test class
                                if 'test-class-added' in elem.m_Classes:
                                    print("  ✅ Found 'test-class-added' class!")
                                    return True

                        print("\n❌ ERROR: 'test-class-added' class not found in any element!")
                        return False

            except Exception as e:
                print(f"Error reading object: {e}")
                pass

    print(f"\nTotal VTAs found: {found_count}")
    print("\n❌ ERROR: AboutClubCard VTA not found!")
    return False

if __name__ == "__main__":
    import sys
    success = verify_patch()
    sys.exit(0 if success else 1)
