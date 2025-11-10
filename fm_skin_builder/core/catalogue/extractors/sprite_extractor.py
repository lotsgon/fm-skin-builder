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
        env = UnityPy.load(str(bundle_path))
        bundle_name = bundle_path.name

        sprites = []

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
            sprite_data = self._extract_sprite_data(data, bundle_name)
            if sprite_data:
                sprites.append(sprite_data)

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
            image = sprite_obj.image
            if image:
                # Convert PIL Image to bytes for later processing
                import io
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                image_data = buf.getvalue()
        except Exception:
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
