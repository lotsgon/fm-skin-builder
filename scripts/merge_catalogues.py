#!/usr/bin/env python3
"""
Merge partial catalogues from parallel processing into a unified catalogue.

This script combines catalogue outputs from multiple parallel jobs, handling:
- Asset deduplication (by hash for sprites/textures, by name for CSS/fonts)
- Thumbnail consolidation
- Metadata aggregation
- Search index rebuilding
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file if it exists."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse {file_path}: {e}")
        return {}


def merge_metadata(partial_dirs: List[Path]) -> Dict[str, Any]:
    """Merge metadata from all partial catalogues."""
    all_bundles = set()
    total_assets = defaultdict(int)
    generated_times = []

    for partial_dir in partial_dirs:
        metadata = load_json(partial_dir / "metadata.json")
        if not metadata:
            continue

        # Collect bundles
        bundles = metadata.get("bundles_scanned", [])
        all_bundles.update(bundles)

        # Sum asset counts
        asset_counts = metadata.get("total_assets", {})
        for asset_type, count in asset_counts.items():
            total_assets[asset_type] += count

        # Track generation times
        if "generated_at" in metadata:
            generated_times.append(metadata["generated_at"])

    # Use the latest generation time
    generated_at = max(generated_times) if generated_times else None

    # Take other fields from the first partial (they should be the same)
    first_metadata = load_json(partial_dirs[0] / "metadata.json") if partial_dirs else {}

    return {
        "catalogue_version": first_metadata.get("catalogue_version", 1),
        "fm_version": first_metadata.get("fm_version", "unknown"),
        "schema_version": first_metadata.get("schema_version", "1.0.0"),
        "generated_at": generated_at or first_metadata.get("generated_at"),
        "bundles_scanned": sorted(list(all_bundles)),
        "total_assets": dict(total_assets),
        "previous_fm_version": first_metadata.get("previous_fm_version"),
        "previous_catalogue_version": first_metadata.get("previous_catalogue_version"),
        "changes_since_previous": first_metadata.get("changes_since_previous"),
    }


def merge_assets_by_hash(
    partial_dirs: List[Path], filename: str, hash_key: str = "content_hash"
) -> List[Dict[str, Any]]:
    """
    Merge assets that use content hashing (sprites, textures).
    Deduplicates by hash, keeping the first occurrence.
    """
    seen_hashes: Set[str] = set()
    merged_assets: List[Dict[str, Any]] = []

    for partial_dir in partial_dirs:
        assets_file = partial_dir / filename
        if not assets_file.exists():
            continue

        try:
            with open(assets_file) as f:
                assets = json.load(f)

            # Handle both list and dict formats
            if isinstance(assets, dict):
                assets = list(assets.values())

            for asset in assets:
                asset_hash = asset.get(hash_key)
                if not asset_hash:
                    # No hash, keep it anyway (shouldn't happen but be defensive)
                    merged_assets.append(asset)
                    continue

                if asset_hash in seen_hashes:
                    # Duplicate - skip it
                    continue

                seen_hashes.add(asset_hash)
                merged_assets.append(asset)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse {assets_file}: {e}")
            continue

    return merged_assets


def merge_assets_by_name(
    partial_dirs: List[Path], filename: str, name_key: str = "name"
) -> List[Dict[str, Any]]:
    """
    Merge assets that use name-based identification (CSS variables, CSS classes, fonts).
    Deduplicates by name, keeping the first occurrence.
    """
    seen_names: Set[str] = set()
    merged_assets: List[Dict[str, Any]] = []

    for partial_dir in partial_dirs:
        assets_file = partial_dir / filename
        if not assets_file.exists():
            continue

        try:
            with open(assets_file) as f:
                assets = json.load(f)

            # Handle both list and dict formats
            if isinstance(assets, dict):
                assets = list(assets.values())

            for asset in assets:
                asset_name = asset.get(name_key)
                if not asset_name:
                    # No name, skip it
                    continue

                if asset_name in seen_names:
                    # Duplicate - skip it
                    continue

                seen_names.add(asset_name)
                merged_assets.append(asset)

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to parse {assets_file}: {e}")
            continue

    return merged_assets


def merge_search_index(partial_dirs: List[Path]) -> Dict[str, Any]:
    """
    Merge search indices from all partial catalogues.
    This requires rebuilding the index from scratch based on merged assets.
    """
    # For now, we'll combine the indices and deduplicate entries
    merged_index: Dict[str, Any] = {
        "color_palette": {
            "css_variables": defaultdict(list),
            "sprites": defaultdict(list),
            "textures": defaultdict(list),
        },
        "tags": defaultdict(lambda: defaultdict(list)),
    }

    for partial_dir in partial_dirs:
        index = load_json(partial_dir / "search-index.json")
        if not index:
            continue

        # Merge color palette
        for asset_type in ["css_variables", "sprites", "textures"]:
            palette = index.get("color_palette", {}).get(asset_type, {})
            for color, assets in palette.items():
                merged_index["color_palette"][asset_type][color].extend(assets)

        # Merge tags
        tags = index.get("tags", {})
        for tag, asset_types in tags.items():
            for asset_type, assets in asset_types.items():
                merged_index["tags"][tag][asset_type].extend(assets)

    # Deduplicate lists in color palette
    for asset_type in ["css_variables", "sprites", "textures"]:
        for color in merged_index["color_palette"][asset_type]:
            merged_index["color_palette"][asset_type][color] = sorted(
                list(set(merged_index["color_palette"][asset_type][color]))
            )

    # Deduplicate lists in tags
    for tag in merged_index["tags"]:
        for asset_type in merged_index["tags"][tag]:
            merged_index["tags"][tag][asset_type] = sorted(
                list(set(merged_index["tags"][tag][asset_type]))
            )

    # Convert defaultdicts to regular dicts for JSON serialization
    return {
        "color_palette": {
            "css_variables": dict(merged_index["color_palette"]["css_variables"]),
            "sprites": dict(merged_index["color_palette"]["sprites"]),
            "textures": dict(merged_index["color_palette"]["textures"]),
        },
        "tags": {
            tag: dict(asset_types) for tag, asset_types in merged_index["tags"].items()
        },
    }


def merge_thumbnails(partial_dirs: List[Path], output_dir: Path):
    """
    Merge thumbnail directories from all partial catalogues.
    Copies all thumbnails, skipping duplicates (same filename).
    """
    output_thumbnails = output_dir / "thumbnails"

    for subdir in ["sprites", "textures"]:
        output_subdir = output_thumbnails / subdir
        output_subdir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for partial_dir in partial_dirs:
            partial_subdir = partial_dir / "thumbnails" / subdir
            if not partial_subdir.exists():
                continue

            for thumbnail in partial_subdir.glob("*"):
                if not thumbnail.is_file():
                    continue

                dest = output_subdir / thumbnail.name

                # Skip if already exists (deduplication)
                if dest.exists():
                    continue

                shutil.copy2(thumbnail, dest)
                copied += 1

        if copied > 0:
            print(f"  Copied {copied} {subdir} thumbnails")


def merge_catalogues(partial_dirs: List[Path], output_dir: Path):
    """
    Merge all partial catalogues into a unified catalogue.

    Args:
        partial_dirs: List of directories containing partial catalogues
        output_dir: Directory to save merged catalogue
    """
    print(f"🔄 Merging {len(partial_dirs)} partial catalogues")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Merge metadata
    print("  Merging metadata...")
    metadata = merge_metadata(partial_dirs)
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # 2. Merge hash-based assets (sprites, textures)
    print("  Merging sprites...")
    sprites = merge_assets_by_hash(partial_dirs, "sprites.json", "content_hash")
    with open(output_dir / "sprites.json", "w") as f:
        json.dump(sprites, f, indent=2)
    print(f"    {len(sprites)} unique sprites")

    print("  Merging textures...")
    textures = merge_assets_by_hash(partial_dirs, "textures.json", "content_hash")
    with open(output_dir / "textures.json", "w") as f:
        json.dump(textures, f, indent=2)
    print(f"    {len(textures)} unique textures")

    # 3. Merge name-based assets (CSS, fonts)
    print("  Merging CSS variables...")
    css_variables = merge_assets_by_name(partial_dirs, "css-variables.json", "name")
    with open(output_dir / "css-variables.json", "w") as f:
        json.dump(css_variables, f, indent=2)
    print(f"    {len(css_variables)} unique variables")

    print("  Merging CSS classes...")
    css_classes = merge_assets_by_name(partial_dirs, "css-classes.json", "name")
    with open(output_dir / "css-classes.json", "w") as f:
        json.dump(css_classes, f, indent=2)
    print(f"    {len(css_classes)} unique classes")

    print("  Merging fonts...")
    fonts = merge_assets_by_name(partial_dirs, "fonts.json", "name")
    with open(output_dir / "fonts.json", "w") as f:
        json.dump(fonts, f, indent=2)
    print(f"    {len(fonts)} unique fonts")

    # 4. Merge search index
    print("  Merging search index...")
    search_index = merge_search_index(partial_dirs)
    with open(output_dir / "search-index.json", "w") as f:
        json.dump(search_index, f, indent=2)

    # 5. Merge thumbnails
    print("  Merging thumbnails...")
    merge_thumbnails(partial_dirs, output_dir)

    print(f"\n✅ Merged catalogue saved to: {output_dir}")
    print(f"   Total unique assets:")
    print(f"   - Sprites: {len(sprites)}")
    print(f"   - Textures: {len(textures)}")
    print(f"   - CSS Variables: {len(css_variables)}")
    print(f"   - CSS Classes: {len(css_classes)}")
    print(f"   - Fonts: {len(fonts)}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge partial catalogues from parallel processing"
    )
    parser.add_argument(
        "--partial-dirs",
        nargs="+",
        type=Path,
        required=True,
        help="Directories containing partial catalogues (e.g., group_0_catalogue/ group_1_catalogue/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for merged catalogue",
    )

    args = parser.parse_args()

    # Validate partial directories
    valid_dirs = [d for d in args.partial_dirs if d.exists() and d.is_dir()]
    if not valid_dirs:
        print("Error: No valid partial catalogue directories found")
        sys.exit(1)

    if len(valid_dirs) < len(args.partial_dirs):
        missing = set(args.partial_dirs) - set(valid_dirs)
        print(f"Warning: Skipping {len(missing)} missing directories:")
        for d in missing:
            print(f"  - {d}")

    merge_catalogues(valid_dirs, args.output)


if __name__ == "__main__":
    main()
