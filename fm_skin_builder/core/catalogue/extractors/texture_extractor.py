"""
Texture Extractor

Extracts texture assets (backgrounds, UI textures) from Unity bundles.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import UnityPy

from .base import BaseAssetExtractor


class TextureExtractor(BaseAssetExtractor):
    """Extracts texture assets from bundles."""

    def extract_from_bundle(self, bundle_path: Path) -> List[Dict[str, Any]]:
        """
        Extract textures from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of texture data dictionaries
        """
        env = UnityPy.load(str(bundle_path))
        bundle_name = bundle_path.name

        textures = []

        for obj in env.objects:
            if obj.type.name != "Texture2D":
                continue

            try:
                data = obj.read()
            except Exception:
                continue

            name = self._get_asset_name(data)
            if not name:
                continue

            texture_data = self._extract_texture_data(data, bundle_name)
            if texture_data:
                textures.append(texture_data)

        return textures

    def _extract_texture_data(
        self, texture_obj: Any, bundle_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract texture data and image.

        Args:
            texture_obj: Unity texture object
            bundle_name: Name of the bundle

        Returns:
            Dictionary with texture metadata and image data
        """
        name = self._get_asset_name(texture_obj)
        if not name:
            return None

        # Get dimensions
        width = getattr(texture_obj, "m_Width", 0)
        height = getattr(texture_obj, "m_Height", 0)

        # Classify texture type based on name patterns
        texture_type = self._classify_texture_type(name)

        # Extract image data
        image_data = None
        try:
            image = texture_obj.image
            if image:
                import io
                buf = io.BytesIO()
                image.save(buf, format='PNG')
                image_data = buf.getvalue()
        except Exception:
            pass

        return {
            "name": name,
            "bundle": bundle_name,
            "type": texture_type,
            "width": width,
            "height": height,
            "image_data": image_data,
            **self._create_default_status(),
        }

    def _classify_texture_type(self, name: str) -> str:
        """
        Classify texture type based on name patterns.

        Args:
            name: Texture name

        Returns:
            Type string: 'background', 'icon', or 'texture'
        """
        name_lower = name.lower()

        if any(pattern in name_lower for pattern in ["bg_", "background", "backdrop"]):
            return "background"
        elif any(pattern in name_lower for pattern in ["icon_", "ico_", "symbol"]):
            return "icon"
        else:
            return "texture"
