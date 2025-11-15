#!/usr/bin/env python3
"""
Clear FM skin builder patch cache.

This script removes cached patch data to force full recomputation.
Use this when you've removed overrides but they're still being applied,
or when you suspect cache corruption.

Usage:
    python scripts/clear_patch_cache.py
"""

from pathlib import Path
import shutil
import sys


def main():
    """Clear all known cache directories used by the FM skin builder patcher."""
    # Adjust paths to your cache locations
    repo_root = Path(__file__).parent.parent
    cache_dirs = [
        repo_root / ".cache" / "patch_cache",
        repo_root / ".cache" / "fm_skin_builder",
        repo_root / ".cache" / "skins",
        repo_root / "cache",
    ]

    found = False
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            print(f"Removing cache: {cache_dir}")
            shutil.rmtree(cache_dir)
            found = True

    if not found:
        print("No known patch cache directories found.")
    else:
        print("\n✅ Cache cleared successfully!")
        print("Run your patch command again to rebuild cache from scratch.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
