#!/usr/bin/env python3
"""
Generate changelog and apply change tracking after merging partial catalogues.

This script:
1. Downloads previous version from R2 if not available locally
2. Runs comparison between versions
3. Applies change tracking to assets
4. Regenerates search index with change filters
5. Saves all updated files
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fm_skin_builder.core.catalogue.version_differ import VersionDiffer
from fm_skin_builder.core.catalogue.search_builder import SearchIndexBuilder
from fm_skin_builder.core.catalogue.models import (
    CSSVariable,
    CSSClass,
    Sprite,
    Texture,
    Font,
)


def load_json(file_path: Path) -> Any:
    """Load JSON file."""
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return [] if file_path.name != "metadata.json" else {}

    with open(file_path) as f:
        return json.load(f)


def save_json(data: Any, file_path: Path, pretty: bool = True):
    """Save JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False)


def download_previous_from_r2(
    fm_version: str, output_base: Path
) -> Optional[Path]:
    """
    Try to download previous version from R2.

    Returns:
        Path to previous version directory if successful, None otherwise
    """
    from fm_skin_builder.core.catalogue.r2_downloader import R2Downloader

    # Get R2 credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_CATALOGUE_BUCKET")

    if not all([account_id, access_key, secret_key, bucket]):
        print("⚠️  R2 credentials not available, cannot download previous version")
        return None

    try:
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        downloader = R2Downloader(
            endpoint_url=endpoint,
            bucket=bucket,
            access_key=access_key,
            secret_key=secret_key,
        )

        # List available versions
        versions = downloader.list_versions("")
        if not versions:
            print("  No previous versions found in R2")
            return None

        # Parse current version for comparison
        from packaging.version import Version, InvalidVersion

        try:
            # Clean version string
            clean_current = fm_version.replace("-beta", "b0")
            if "-v" in clean_current:
                clean_current = clean_current.split("-v")[0]
            current = Version(clean_current)
        except (InvalidVersion, Exception) as e:
            print(f"  Cannot parse current version: {e}")
            return None

        # Find most recent previous version
        candidates = []
        for ver in versions:
            if ver == fm_version:
                continue

            try:
                clean_ver = ver.replace("-beta", "b0")
                if "-v" in clean_ver:
                    clean_ver = clean_ver.split("-v")[0]
                parsed = Version(clean_ver)

                if parsed < current:
                    candidates.append((parsed, ver))
            except (InvalidVersion, Exception):
                continue

        if not candidates:
            print("  No previous stable versions found")
            return None

        # Get most recent
        candidates.sort(reverse=True)
        prev_version = candidates[0][1]

        print(f"  Downloading previous version: {prev_version}")
        prev_dir = output_base / prev_version

        if downloader.download_version(prev_version, output_base, ""):
            print(f"  ✅ Downloaded {prev_version}")
            return prev_dir
        else:
            print(f"  ❌ Failed to download {prev_version}")
            return None

    except Exception as e:
        print(f"  ⚠️  Error accessing R2: {e}")
        return None


def find_local_previous(fm_version: str, output_base: Path) -> Optional[Path]:
    """Find previous version in local output directory."""
    if not output_base.exists():
        return None

    version_dirs = [
        d
        for d in output_base.iterdir()
        if d.is_dir() and d.name != fm_version and (d / "metadata.json").exists()
    ]

    if not version_dirs:
        return None

    # Sort by name (simple version comparison)
    version_dirs.sort(reverse=True)
    prev_dir = version_dirs[0]

    print(f"  Found local previous version: {prev_dir.name}")
    return prev_dir


def apply_change_tracking(
    catalogue_dir: Path, changelog: Dict[str, Any]
) -> None:
    """
    Apply change tracking from changelog to asset files.

    Args:
        catalogue_dir: Directory containing catalogue files
        changelog: Changelog dictionary from comparison
    """
    fm_version = changelog.get("to_version", "unknown")
    changes_by_type = changelog.get("changes_by_type", {})

    # Load all asset files
    css_vars_raw = load_json(catalogue_dir / "css-variables.json")
    css_classes_raw = load_json(catalogue_dir / "css-classes.json")
    sprites_raw = load_json(catalogue_dir / "sprites.json")
    textures_raw = load_json(catalogue_dir / "textures.json")
    fonts_raw = load_json(catalogue_dir / "fonts.json")

    # Apply changes to CSS variables
    if "css_variables" in changes_by_type:
        changes = changes_by_type["css_variables"]
        added = {c["name"] for c in changes.get("added", [])}
        modified = {c["name"]: c for c in changes.get("modified", [])}

        for var in css_vars_raw:
            if var["name"] in added:
                var["change_status"] = "new"
                var["changed_in_version"] = fm_version
            elif var["name"] in modified:
                var["change_status"] = "modified"
                var["changed_in_version"] = fm_version
            else:
                var["change_status"] = "unchanged"

    # Apply changes to CSS classes
    if "css_classes" in changes_by_type:
        changes = changes_by_type["css_classes"]
        added = {c["name"] for c in changes.get("added", [])}
        modified = {c["name"] for c in changes.get("modified", [])}

        for cls in css_classes_raw:
            if cls["name"] in added:
                cls["change_status"] = "new"
                cls["changed_in_version"] = fm_version
            elif cls["name"] in modified:
                cls["change_status"] = "modified"
                cls["changed_in_version"] = fm_version
            else:
                cls["change_status"] = "unchanged"

    # Apply changes to sprites
    if "sprites" in changes_by_type:
        changes = changes_by_type["sprites"]
        added = {c["name"] for c in changes.get("added", [])}
        modified = {c["name"]: c for c in changes.get("modified", [])}

        for sprite in sprites_raw:
            if sprite["name"] in added:
                sprite["change_status"] = "new"
                sprite["changed_in_version"] = fm_version
            elif sprite["name"] in modified:
                sprite["change_status"] = "modified"
                sprite["changed_in_version"] = fm_version
                mod = modified[sprite["name"]]
                if "old_hash" in mod:
                    sprite["previous_content_hash"] = mod["old_hash"]
            else:
                sprite["change_status"] = "unchanged"

    # Apply changes to textures
    if "textures" in changes_by_type:
        changes = changes_by_type["textures"]
        added = {c["name"] for c in changes.get("added", [])}
        modified = {c["name"]: c for c in changes.get("modified", [])}

        for texture in textures_raw:
            if texture["name"] in added:
                texture["change_status"] = "new"
                texture["changed_in_version"] = fm_version
            elif texture["name"] in modified:
                texture["change_status"] = "modified"
                texture["changed_in_version"] = fm_version
                mod = modified[texture["name"]]
                if "old_hash" in mod:
                    texture["previous_content_hash"] = mod["old_hash"]
            else:
                texture["change_status"] = "unchanged"

    # Apply changes to fonts
    if "fonts" in changes_by_type:
        changes = changes_by_type["fonts"]
        added = {c["name"] for c in changes.get("added", [])}
        modified = {c["name"] for c in changes.get("modified", [])}

        for font in fonts_raw:
            if font["name"] in added:
                font["change_status"] = "new"
                font["changed_in_version"] = fm_version
            elif font["name"] in modified:
                font["change_status"] = "modified"
                font["changed_in_version"] = fm_version
            else:
                font["change_status"] = "unchanged"

    # Save updated files
    save_json(css_vars_raw, catalogue_dir / "css-variables.json")
    save_json(css_classes_raw, catalogue_dir / "css-classes.json")
    save_json(sprites_raw, catalogue_dir / "sprites.json")
    save_json(textures_raw, catalogue_dir / "textures.json")
    save_json(fonts_raw, catalogue_dir / "fonts.json")

    # Count changes
    total_new = sum(1 for v in css_vars_raw if v.get("change_status") == "new")
    total_new += sum(1 for c in css_classes_raw if c.get("change_status") == "new")
    total_new += sum(1 for s in sprites_raw if s.get("change_status") == "new")
    total_new += sum(1 for t in textures_raw if t.get("change_status") == "new")
    total_new += sum(1 for f in fonts_raw if f.get("change_status") == "new")

    total_modified = sum(
        1 for v in css_vars_raw if v.get("change_status") == "modified"
    )
    total_modified += sum(
        1 for c in css_classes_raw if c.get("change_status") == "modified"
    )
    total_modified += sum(1 for s in sprites_raw if s.get("change_status") == "modified")
    total_modified += sum(
        1 for t in textures_raw if t.get("change_status") == "modified"
    )
    total_modified += sum(1 for f in fonts_raw if f.get("change_status") == "modified")

    print(f"  ✅ Applied change tracking: {total_new} new, {total_modified} modified")

    # Rebuild search index with change filters
    print("  Rebuilding search index with change filters...")

    # Convert raw dicts to models for search builder
    css_vars = [CSSVariable(**v) for v in css_vars_raw]
    css_classes = [CSSClass(**c) for c in css_classes_raw]
    sprites = [Sprite(**s) for s in sprites_raw]
    textures = [Texture(**t) for t in textures_raw]
    fonts = [Font(**f) for f in fonts_raw]

    search_builder = SearchIndexBuilder()
    search_index = search_builder.build_index(
        css_vars, css_classes, sprites, textures, fonts
    )

    save_json(search_index, catalogue_dir / "search-index.json")
    print("  ✅ Updated search index")


def generate_changelog(catalogue_dir: Path, fm_version: str):
    """
    Generate changelog for a merged catalogue.

    Args:
        catalogue_dir: Directory containing merged catalogue
        fm_version: FM version string
    """
    print(f"\n📊 Generating changelog for {fm_version}")

    output_base = catalogue_dir.parent

    # Try to find previous version
    prev_dir = find_local_previous(fm_version, output_base)

    if not prev_dir:
        print("  Attempting to download previous version from R2...")
        prev_dir = download_previous_from_r2(fm_version, output_base)

    if not prev_dir:
        print("  ⚠️  No previous version found - skipping changelog generation")
        print("  (This is normal for the first version)")
        return

    # Generate changelog
    print(f"\n📝 Comparing {prev_dir.name} → {fm_version}")

    differ = VersionDiffer(prev_dir, catalogue_dir)
    differ.load_catalogues()
    changelog = differ.compare()

    # Save changelog
    changelog_path = catalogue_dir / "changelog-summary.json"
    save_json(changelog, changelog_path)
    print(f"  ✅ Saved changelog: {changelog_path}")

    # Generate HTML report
    html_report = differ.generate_html_report(changelog)
    html_path = catalogue_dir / "changelog.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    print(f"  ✅ Saved HTML report: {html_path}")

    # Apply change tracking to assets
    print("\n🔄 Applying change tracking to assets...")
    apply_change_tracking(catalogue_dir, changelog)

    # Update metadata
    metadata_path = catalogue_dir / "metadata.json"
    metadata = load_json(metadata_path)
    metadata["previous_fm_version"] = prev_dir.name
    metadata["changes_since_previous"] = changelog["summary"]
    save_json(metadata, metadata_path)
    print("  ✅ Updated metadata")

    print(f"\n✅ Changelog generation complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate changelog after merging partial catalogues"
    )
    parser.add_argument(
        "--catalogue-dir",
        type=Path,
        required=True,
        help="Path to merged catalogue directory",
    )
    parser.add_argument(
        "--fm-version", type=str, required=True, help="FM version string"
    )

    args = parser.parse_args()

    if not args.catalogue_dir.exists():
        print(f"Error: Catalogue directory not found: {args.catalogue_dir}")
        sys.exit(1)

    try:
        generate_changelog(args.catalogue_dir, args.fm_version)
    except Exception as e:
        print(f"\n❌ Error generating changelog: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
