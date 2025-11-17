#!/usr/bin/env python3
"""Test set_raw_data WITHOUT calling obj.read() first."""

from pathlib import Path
import UnityPy

def test_set_raw_without_read():
    """Test if NOT calling read() before set_raw_data() prevents corruption."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    output_path = Path("test_output/ui-panelids-uxml_assets_all_noread.bundle")

    print(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    # First pass: find AboutClubCard and get its raw data WITHOUT calling read()
    target_obj = None
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            # We need to check the name, but we'll do it carefully
            # Peek at the name without full read
            try:
                name = obj.peek_name()
                if name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard (using peek_name)")
                    target_obj = obj
                    break
            except:
                pass

    if not target_obj:
        print("ERROR: AboutClubCard not found!")
        return False

    # Get raw data WITHOUT calling read()
    raw_data = target_obj.get_raw_data()
    print(f"  Original raw data size: {len(raw_data)} bytes")

    # Set it back unchanged, but WITHOUT having called read()
    target_obj.set_raw_data(raw_data)
    print("  Set raw data back (without calling read())")

    # Save the bundle
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(env.file.save())

    print(f"\n✅ Saved bundle to: {output_path}")

    # Try to load it back
    print("\nLoading saved bundle...")
    env2 = UnityPy.load(str(output_path))

    for obj in env2.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                name = obj.peek_name()
                if name == "AboutClubCard":
                    print("\n✓ Found AboutClubCard in saved bundle")

                    # Try to read it
                    try:
                        data = obj.read()
                        print("  ✅ Successfully read() the object!")

                        # Get raw data size
                        raw_data2 = obj.get_raw_data()
                        print(f"  Raw data size: {len(raw_data2)} bytes")

                        # Check if it matches original
                        if len(raw_data2) == len(raw_data):
                            print("  ✅ Size matches original!")
                            return True
                        else:
                            print(f"  ❌ Size changed: {len(raw_data)} → {len(raw_data2)} bytes")
                            return False

                    except Exception as e:
                        print(f"  ❌ Error reading object: {e}")
                        return False
            except:
                pass

    print("❌ AboutClubCard not found in saved bundle!")
    return False

if __name__ == "__main__":
    import sys
    success = test_set_raw_without_read()
    sys.exit(0 if success else 1)
