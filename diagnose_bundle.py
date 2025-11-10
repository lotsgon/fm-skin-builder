#!/usr/bin/env python3
"""
Diagnostic script to identify which asset causes segfaults.

This script processes one texture/sprite at a time to isolate the problematic asset.
"""

from pathlib import Path
import sys
import UnityPy

def diagnose_bundle(bundle_path: Path):
    """Process bundle one asset at a time to find the culprit."""
    print(f"\n🔍 Diagnosing: {bundle_path.name}")
    print("=" * 80)

    try:
        env = UnityPy.load(str(bundle_path))
    except Exception as e:
        print(f"❌ Failed to load bundle: {e}")
        return

    # Process textures
    print("\n📷 Processing Texture2D objects...")
    for i, obj in enumerate(env.objects):
        if obj.type.name != "Texture2D":
            continue

        try:
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)
            width = getattr(data, "m_Width", 0)
            height = getattr(data, "m_Height", 0)
            tex_format = getattr(data, "m_TextureFormat", "unknown")

            print(f"\n  [{i}] {name}")
            print(f"      Size: {width}x{height}")
            print(f"      Format: {tex_format}")

            # Try to access image - this is where crashes happen
            print(f"      Attempting to access .image property...", end=" ")
            sys.stdout.flush()

            try:
                image = data.image
                if image:
                    print(f"✅ OK ({image.width}x{image.height})")
                else:
                    print("⚠️  No image data")
            except Exception as e:
                print(f"❌ Error: {e}")

        except Exception as e:
            print(f"  ❌ Error reading texture {i}: {e}")

    print("\n" + "=" * 80)
    print("✅ Diagnosis complete! If you see this, no segfault occurred.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_bundle.py <bundle_path>")
        sys.exit(1)

    bundle = Path(sys.argv[1])
    if not bundle.exists():
        print(f"❌ Bundle not found: {bundle}")
        sys.exit(1)

    diagnose_bundle(bundle)
