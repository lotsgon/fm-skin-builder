#!/usr/bin/env python3
"""Verify that the V2 patched bundle contains the modified CSS class."""

from pathlib import Path
import UnityPy


def verify_patch_v2():
    """Verify AboutClubCard was patched correctly with V2."""
    bundle_path = Path("test_output/ui-panelids-uxml_assets_all_v2.bundle")

    if not bundle_path.exists():
        print("ERROR: Output bundle not found!")
        return False

    print(f"Loading V2 patched bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    print(f"Total objects in bundle: {len(list(env.objects))}\n")

    found_count = 0
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = hasattr(data, "m_VisualElementAssets") or hasattr(
                    data, "m_TemplateAssets"
                )

                if is_vta:
                    found_count += 1
                    asset_name = getattr(data, "m_Name", "")
                    if asset_name == "AboutClubCard":
                        print("✓ Found AboutClubCard VTA\n")

                        if hasattr(data, "m_VisualElementAssets"):
                            print(f"Visual elements: {len(data.m_VisualElementAssets)}")
                            for i, elem in enumerate(data.m_VisualElementAssets):
                                print(f"\n  Element {i} (ID {elem.m_Id}):")
                                print(
                                    f"    Type: {getattr(elem, 'm_FullTypeName', 'N/A')}"
                                )
                                print(f"    Classes: {elem.m_Classes}")

                                # Check for our test class
                                if "test-class-added" in elem.m_Classes:
                                    print("    ✅ Found 'test-class-added' class!")

                        if hasattr(data, "m_TemplateAssets"):
                            print(f"\nTemplate assets: {len(data.m_TemplateAssets)}")
                            for i, elem in enumerate(data.m_TemplateAssets):
                                print(f"\n  Template {i} (ID {elem.m_Id}):")
                                print(
                                    f"    Alias: {getattr(elem, 'm_TemplateAlias', 'N/A')}"
                                )
                                print(f"    Classes: {elem.m_Classes}")

                        # Verify the class was added
                        elem_with_class = next(
                            (
                                e
                                for e in data.m_VisualElementAssets
                                if "test-class-added" in e.m_Classes
                            ),
                            None,
                        )

                        if elem_with_class:
                            print(
                                f"\n✅ SUCCESS: 'test-class-added' class found on element {elem_with_class.m_Id}!"
                            )
                            return True
                        else:
                            print(
                                "\n❌ ERROR: 'test-class-added' class not found in any element!"
                            )
                            return False

            except Exception as e:
                print(f"Error reading object: {e}")
                pass

    print(f"\nTotal VTAs found: {found_count}")
    print("\n❌ ERROR: AboutClubCard VTA not found!")
    return False


if __name__ == "__main__":
    import sys

    success = verify_patch_v2()
    sys.exit(0 if success else 1)
