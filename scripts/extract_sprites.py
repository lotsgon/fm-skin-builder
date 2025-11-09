#!/usr/bin/env python3
"""Extract individual sprites from Unity sprite atlases as PNG files.

This tool extracts sprites from sprite atlas bundles, saving each sprite as a separate
PNG file with its original name. This makes it easy to:
- Visualize what each sprite looks like
- Reference sprite names when creating icon mappings
- Choose appropriate replacement icons

Usage:
    python scripts/extract_sprites.py --bundle bundles/ui-iconspriteatlases_assets_4x.bundle --output extracted_sprites/
    python scripts/extract_sprites.py --bundle-dir bundles --pattern "ui-iconspriteatlases*.bundle" --output extracted_sprites/
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
import glob

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import UnityPy
    from PIL import Image
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Install with: pip install UnityPy Pillow")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


def extract_sprites_from_bundle(bundle_path: Path, output_dir: Path, scale: str = "") -> int:
    """Extract all sprites from a bundle as individual PNG files.

    Args:
        bundle_path: Path to the Unity bundle file
        output_dir: Directory to save extracted PNG files
        scale: Optional scale suffix (e.g., "1x", "2x") to include in output folder

    Returns:
        Number of sprites extracted
    """
    if not bundle_path.exists():
        log.error(f"Bundle not found: {bundle_path}")
        return 0

    log.info(f"Loading bundle: {bundle_path}")
    env = UnityPy.load(str(bundle_path))

    # Create output directory
    if scale:
        sprite_output_dir = output_dir / scale
    else:
        sprite_output_dir = output_dir

    sprite_output_dir.mkdir(parents=True, exist_ok=True)

    # First, parse all sprite atlases to get sprite information
    from fm_skin_builder.core.textures import _parse_sprite_atlas
    sprite_atlas_map = _parse_sprite_atlas(env)

    if not sprite_atlas_map:
        log.warning(f"No sprite atlases found in {bundle_path.name}")
        return 0

    log.info(f"Found {len(sprite_atlas_map)} sprites in atlases")

    # Build a mapping of texture path_id to texture object
    textures_by_pathid: Dict[int, object] = {}
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            try:
                tex = obj.read()
                path_id = obj.path_id
                if path_id < 0:
                    path_id = path_id & 0xFFFFFFFFFFFFFFFF
                textures_by_pathid[path_id] = tex
            except Exception as e:
                log.debug(f"Failed to read texture: {e}")

    log.info(f"Found {len(textures_by_pathid)} textures")

    # Extract each sprite
    extracted = 0
    for sprite_name, atlas_info in sprite_atlas_map.items():
        try:
            # Get the atlas texture
            atlas_tex = textures_by_pathid.get(atlas_info.texture_path_id)
            if not atlas_tex:
                log.debug(f"Texture not found for sprite '{sprite_name}'")
                continue

            # Get the atlas as a PIL image
            atlas_image = atlas_tex.image
            if not atlas_image:
                log.debug(f"Could not get image for sprite '{sprite_name}'")
                continue

            atlas_width = atlas_image.width
            atlas_height = atlas_image.height

            # Extract sprite rect from atlas info
            rect_x = atlas_info.rect_x
            rect_y = atlas_info.rect_y
            rect_width = atlas_info.rect_width
            rect_height = atlas_info.rect_height

            # Convert Unity bottom-left origin to PIL top-left origin
            pil_top = atlas_height - (rect_y + rect_height)
            pil_left = rect_x
            pil_right = rect_x + rect_width
            pil_bottom = pil_top + rect_height

            # Crop the sprite from the atlas
            sprite_image = atlas_image.crop(
                (pil_left, pil_top, pil_right, pil_bottom))

            # Sanitize filename (replace invalid characters)
            safe_name = sprite_name.replace(
                '/', '_').replace('\\', '_').replace(':', '_')
            output_path = sprite_output_dir / f"{safe_name}.png"

            # Save the sprite
            sprite_image.save(output_path)
            extracted += 1

            if extracted % 100 == 0:
                log.info(f"Extracted {extracted} sprites...")

        except Exception as e:
            log.warning(f"Failed to extract sprite '{sprite_name}': {e}")

    log.info(f"✓ Extracted {extracted} sprites to {sprite_output_dir}")
    return extracted


def main():
    parser = argparse.ArgumentParser(
        description="Extract sprites from Unity sprite atlas bundles as PNG files"
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Path to a specific bundle file to extract"
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        help="Directory containing bundle files"
    )
    parser.add_argument(
        "--pattern",
        default="ui-iconspriteatlases_assets_*.bundle",
        help="Glob pattern to match bundle files (default: ui-iconspriteatlases_assets_*.bundle)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("extracted_sprites"),
        help="Output directory for extracted PNG files (default: extracted_sprites)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which bundles to process
    bundles_to_process: List[Tuple[Path, str]] = []

    if args.bundle:
        # Single bundle specified
        bundles_to_process.append((args.bundle, ""))
    elif args.bundle_dir:
        # Directory with pattern
        pattern_path = args.bundle_dir / args.pattern
        bundle_files = sorted(glob.glob(str(pattern_path)))

        if not bundle_files:
            log.error(f"No bundles found matching pattern: {pattern_path}")
            return 1

        # Extract scale from bundle name (e.g., "1x", "2x", "3x", "4x")
        for bundle_path in bundle_files:
            bundle_path = Path(bundle_path)
            # Try to extract scale from filename
            name = bundle_path.stem
            scale = ""
            for s in ["1x", "2x", "3x", "4x"]:
                if s in name:
                    scale = s
                    break
            bundles_to_process.append((bundle_path, scale))
    else:
        log.error("Must specify either --bundle or --bundle-dir")
        return 1

    # Process each bundle
    total_extracted = 0
    log.info("=" * 80)
    log.info(f"Extracting sprites from {len(bundles_to_process)} bundle(s)")
    log.info("=" * 80)

    for bundle_path, scale in bundles_to_process:
        extracted = extract_sprites_from_bundle(
            bundle_path, args.output, scale)
        total_extracted += extracted

    log.info("=" * 80)
    log.info(f"✓ Total: {total_extracted} sprites extracted to {args.output}")
    log.info("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
