#!/usr/bin/env python3
"""Test if UnityPy can roundtrip AboutClubCard without modifications."""

from pathlib import Path
import UnityPy

def test_roundtrip():
    """Test loading and saving without modifications."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    output_path = Path("test_output/ui-panelids-uxml_assets_all_roundtrip.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    # Find AboutClubCard and get its raw data
    orig_raw_size = None
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard")

                    # Get raw data
                    raw_data = obj.get_raw_data()
                    orig_raw_size = len(raw_data)
                    print(f"  Original raw data size: {orig_raw_size} bytes")

                    # Set it back unchanged
                    obj.set_raw_data(raw_data)
                    print("  Set raw data back (unchanged)")

                    break
            except:
                pass

    if orig_raw_size is None:
        print("ERROR: AboutClubCard not found!")
        return False

    # Save the bundle
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(env.file.save())

    print(f"\n✅ Saved roundtrip bundle to: {output_path}")

    # Try to load it back
    print("\nLoading roundtrip bundle...")
    env2 = UnityPy.load(str(output_path))

    for obj in env2.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                if hasattr(data, "m_Name") and data.m_Name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard in roundtrip bundle")

                    # Get raw data
                    raw_data2 = obj.get_raw_data()
                    print(f"  Roundtrip raw data size: {len(raw_data2)} bytes")

                    # Check if it's the same size
                    if len(raw_data2) == orig_raw_size:
                        print("  ✅ Size matches original!")
                    else:
                        print(f"  ❌ Size changed: {orig_raw_size} → {len(raw_data2)} bytes")

                    # Check visual elements
                    if hasattr(data, "m_VisualElementAssets"):
                        print(f"  Visual elements: {len(data.m_VisualElementAssets)}")
                    if hasattr(data, "m_TemplateAssets"):
                        print(f"  Template assets: {len(data.m_TemplateAssets)}")

                    return True

            except Exception as e:
                print(f"  ❌ Error reading AboutClubCard: {e}")
                try:
                    raw_data2 = obj.get_raw_data()
                    print(f"  Got raw data anyway: {len(raw_data2)} bytes")
                except:
                    pass
                return False

    print("❌ AboutClubCard not found in roundtrip bundle!")
    return False

if __name__ == "__main__":
    import sys
    success = test_roundtrip()
    sys.exit(0 if success else 1)
