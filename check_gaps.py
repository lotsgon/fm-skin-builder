#!/usr/bin/env python3
"""Check what's in the gaps between elements."""

from pathlib import Path
import UnityPy

def check_gaps():
    """Check gaps between elements."""
    bundle_path = Path("test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle")
    env = UnityPy.load(str(bundle_path))

    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            try:
                data = obj.read()
                is_vta = (hasattr(data, "m_VisualElementAssets") or hasattr(data, "m_TemplateAssets"))

                if is_vta:
                    asset_name = getattr(data, "m_Name", "")
                    if asset_name == "AboutClubCard":
                        print("Found AboutClubCard\n")

                        raw_data = obj.get_raw_data()

                        # Element 0 ends at 289, element 1 starts at 292
                        print("Gap 1 (between element 0 and 1):")
                        gap1 = raw_data[289:292]
                        print(f"  Bytes: {' '.join(f'{b:02x}' for b in gap1)}")
                        print(f"  As ints: {list(gap1)}")

                        # Element 1 ends at 389, element 2 starts at 392
                        print("\nGap 2 (between element 1 and 2):")
                        gap2 = raw_data[389:392]
                        print(f"  Bytes: {' '.join(f'{b:02x}' for b in gap2)}")
                        print(f"  As ints: {list(gap2)}")

                        # Element 2 ends at 509, what's after?
                        print("\nAfter element 2 (pos 509-515):")
                        after_elem2 = raw_data[509:515]
                        print(f"  Bytes: {' '.join(f'{b:02x}' for b in after_elem2)}")
                        print(f"  As ints: {list(after_elem2)}")

                        return

            except Exception:
                pass

if __name__ == "__main__":
    check_gaps()
