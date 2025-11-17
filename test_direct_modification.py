#!/usr/bin/env python3
"""Test modifying data object directly instead of using raw binary."""

from pathlib import Path
import UnityPy

def test_direct_modification():
    """Test modifying m_Classes directly on the data object."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    output_path = Path("test_output/ui-panelids-uxml_assets_all_direct.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    # Find AboutClubCard
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard")

                    if hasattr(data, "m_VisualElementAssets"):
                        print(f"  Visual elements: {len(data.m_VisualElementAssets)}")

                        # Try to modify the second element's classes
                        if len(data.m_VisualElementAssets) > 1:
                            elem = data.m_VisualElementAssets[1]
                            print(f"\n  Element {elem.m_Id}:")
                            print(f"    Original classes: {elem.m_Classes}")

                            # Try to modify classes directly
                            try:
                                elem.m_Classes.append('test-class-added')
                                print(f"    Modified classes: {elem.m_Classes}")
                            except Exception as e:
                                print(f"    ❌ Could not modify classes: {e}")
                                # Try alternative approach
                                try:
                                    new_classes = list(elem.m_Classes) + ['test-class-added']
                                    elem.m_Classes = new_classes
                                    print(f"    Modified classes (alt): {elem.m_Classes}")
                                except Exception as e2:
                                    print(f"    ❌ Could not modify classes (alt): {e2}")
                                    return False

                            # Save the data object
                            print("\n  Calling data.save()...")
                            data.save()
                            print("  ✓ data.save() completed")

                    break
            except:
                pass

    # Save the bundle
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(env.file.save())

    print(f"\n✅ Saved modified bundle to: {output_path}")

    # Try to load it back
    print("\nLoading modified bundle...")
    env2 = UnityPy.load(str(output_path))

    for obj in env2.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard in modified bundle")

                    if hasattr(data, "m_VisualElementAssets"):
                        print(f"  Visual elements: {len(data.m_VisualElementAssets)}")

                        if len(data.m_VisualElementAssets) > 1:
                            elem = data.m_VisualElementAssets[1]
                            print(f"\n  Element {elem.m_Id}:")
                            print(f"    Classes: {elem.m_Classes}")

                            # Check for our test class
                            if 'test-class-added' in elem.m_Classes:
                                print("    ✅ Found 'test-class-added' class!")
                                return True
                            else:
                                print("    ❌ 'test-class-added' class not found!")
                                return False

            except Exception as e:
                print(f"  ❌ Error reading AboutClubCard: {e}")
                import traceback
                traceback.print_exc()
                return False

    print("❌ AboutClubCard not found in modified bundle!")
    return False

if __name__ == "__main__":
    import sys
    success = test_direct_modification()
    sys.exit(0 if success else 1)
