"""
Sprite Extractor

Extracts sprite/icon assets from Unity bundles with image data and metadata.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import UnityPy

from .base import BaseAssetExtractor
from ..models import Sprite


class SpriteExtractor(BaseAssetExtractor):
    """Extracts sprite assets from bundles."""

    def extract_from_bundle(self, bundle_path: Path) -> List[Dict[str, Any]]:
        """
        Extract sprites from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of sprite data dictionaries (not full Sprite models yet,
            as they need image processing for hashes and thumbnails)
        """
        import gc

        sprites = []

        try:
            env = UnityPy.load(str(bundle_path))
        except Exception as e:
            # If we can't load the bundle, return empty list
            return sprites

        bundle_name = bundle_path.name

        try:
            for obj in env.objects:
                if obj.type.name != "Sprite":
                    continue

                try:
                    data = obj.read()
                except Exception:
                    continue

                name = self._get_asset_name(data)
                if not name:
                    continue

                # Extract sprite metadata
                try:
                    sprite_data = self._extract_sprite_data(data, bundle_name)
                    if sprite_data:
                        sprites.append(sprite_data)
                except Exception:
                    # Skip problematic sprites
                    continue

            # Also check SpriteAtlas
            for obj in env.objects:
                if obj.type.name != "SpriteAtlas":
                    continue

                try:
                    data = obj.read()
                except Exception:
                    continue

                atlas_name = self._get_asset_name(data) or "UnnamedAtlas"
                packed_names = getattr(data, "m_PackedSpriteNamesToIndex", None)

                if packed_names:
                    for sprite_name in list(packed_names):
                        if sprite_name:
                            # Mark this as from an atlas
                            sprites.append({
                                "name": str(sprite_name),
                                "atlas": atlas_name,
                                "bundle": bundle_name,
                                "has_vertex_data": False,  # Atlas sprites typically don't
                                "image_data": None,  # Atlas sprites need special handling
                                **self._create_default_status(),
                            })
        finally:
            # Clean up UnityPy environment
            try:
                del env
            except:
                pass
            gc.collect()

        return sprites

    def _extract_sprite_data(
        self, sprite_obj: Any, bundle_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract sprite data and image.

        Args:
            sprite_obj: Unity sprite object
            bundle_name: Name of the bundle

        Returns:
            Dictionary with sprite metadata and image data
        """
        name = self._get_asset_name(sprite_obj)
        if not name:
            return None

        # Check for vertex data (vector sprites)
        has_vertex_data = self._has_vertex_data(sprite_obj)

        # Get dimensions
        rect = getattr(sprite_obj, "m_Rect", None)
        width = 0
        height = 0
        if rect:
            width = int(getattr(rect, "width", 0))
            height = int(getattr(rect, "height", 0))

        # Extract image data
        image_data = None
        try:
            # Check if image property exists before accessing
            if not hasattr(sprite_obj, 'image'):
                return {
                    "name": name,
                    "bundle": bundle_name,
                    "has_vertex_data": has_vertex_data,
                    "width": width,
                    "height": height,
                    "image_data": None,
                    "atlas": None,
                    **self._create_default_status(),
                }

            # Access image - this is where segfaults often occur
            image = sprite_obj.image
            if image:
                # For large images, convert to thumbnail immediately to save memory
                # Don't store full 4K+ images in memory
                from PIL import Image
                import io

                # Create a copy to avoid modifying original
                img_copy = image.copy()

                # If image is very large, create thumbnail immediately
                if img_copy.width > 2048 or img_copy.height > 2048:
                    # Create thumbnail at 2048x2048 max (will be thumbnailed again to 256x256 later)
                    img_copy.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

                # Convert to PNG bytes
                buf = io.BytesIO()
                img_copy.save(buf, format='PNG')
                image_data = buf.getvalue()

                # Clean up
                del img_copy
                del buf
        except Exception as e:
            # Image extraction failed, continue without image data
            # Don't fail the entire extraction for one bad image
            pass

        return {
            "name": name,
            "bundle": bundle_name,
            "has_vertex_data": has_vertex_data,
            "width": width,
            "height": height,
            "image_data": image_data,
            "atlas": None,
            **self._create_default_status(),
        }

    def _has_vertex_data(self, sprite_obj: Any) -> bool:
        """
        Check if sprite has custom vertex data (vector sprite).

        Args:
            sprite_obj: Unity sprite object

        Returns:
            True if sprite has vertex data
        """
        try:
            rd = getattr(sprite_obj, "m_RD", None)
            if not rd:
                return False

            vertex_data = getattr(rd, "m_VertexData", None)
            if not vertex_data:
                return False

            vertex_count = getattr(vertex_data, "m_VertexCount", 0)
            return vertex_count > 0
        except Exception:
            return False
