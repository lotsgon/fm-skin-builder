"""
Sprite Extractor

Extracts sprite/icon assets from Unity bundles with image data and metadata.
Handles both standalone sprites and sprites from sprite atlases.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import UnityPy
from PIL import Image
import io

from .base import BaseAssetExtractor
from ...textures import _parse_sprite_atlas


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
        except Exception:
            # If we can't load the bundle, return empty list
            return sprites

        bundle_name = bundle_path.name

        try:
            # Extract standalone sprites
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

            # Extract sprites from sprite atlases
            try:
                sprite_atlas_map = _parse_sprite_atlas(env)

                if sprite_atlas_map:
                    # Build texture cache
                    textures_by_pathid: Dict[int, Any] = {}
                    for obj in env.objects:
                        if obj.type.name == "Texture2D":
                            try:
                                tex = obj.read()
                                path_id = obj.path_id
                                if path_id < 0:
                                    path_id = path_id & 0xFFFFFFFFFFFFFFFF
                                textures_by_pathid[path_id] = tex
                            except Exception:
                                pass

                    # Extract each sprite from atlas
                    for sprite_name, atlas_info in sprite_atlas_map.items():
                        try:
                            sprite_data = self._extract_atlas_sprite(
                                sprite_name, atlas_info, textures_by_pathid, bundle_name
                            )
                            if sprite_data:
                                sprites.append(sprite_data)
                        except Exception:
                            # Skip problematic atlas sprites
                            continue

            except Exception:
                # If atlas parsing fails, continue with what we have
                pass

        finally:
            # Clean up UnityPy environment
            try:
                del env
            except Exception:
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
            # Sprites reference textures via m_RD.texture
            # We need to get the texture, then crop the sprite's rect from it
            texture_ref = getattr(sprite_obj, "m_RD", None)
            if not texture_ref:
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

            texture = getattr(texture_ref, "texture", None)

            # Check if texture PPtr is valid (not null)
            # PPtr with m_PathID=0 means null reference
            if not texture or (hasattr(texture, 'm_PathID') and texture.m_PathID == 0):
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

            # Read the actual texture object
            try:
                tex_data = texture.read()
                tex_format = getattr(tex_data, "m_TextureFormat", None)

                # Skip problematic formats (same as texture extractor)
                problematic_formats = [
                    48,
                    49,
                    50,
                    51,
                    52,
                    53,
                    34,
                    45,
                    46,
                    47,
                    26,
                    30,
                    31,
                    32,
                    33,
                ]

                if tex_format in problematic_formats:
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

                # Also check by name if format is an enum
                if hasattr(tex_format, "name"):
                    format_name = tex_format.name
                    if any(
                        problematic in format_name
                        for problematic in ["ASTC", "ETC", "PVRTC", "BC7"]
                    ):
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

                # Get the texture image
                texture_image = tex_data.image
                if not texture_image:
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

                # Crop the sprite's rect from the texture
                # (standalone sprites work just like atlas sprites)
                tex_width = texture_image.width
                tex_height = texture_image.height

                # Convert Unity bottom-left origin to PIL top-left origin
                pil_top = tex_height - (rect.y + height)
                pil_left = int(rect.x)
                pil_right = int(rect.x + width)
                pil_bottom = int(pil_top + height)

                # Ensure bounds are valid
                pil_top = max(0, int(pil_top))
                pil_left = max(0, pil_left)
                pil_right = min(tex_width, pil_right)
                pil_bottom = min(tex_height, pil_bottom)

                # Crop the sprite from the texture
                sprite_image = texture_image.crop(
                    (pil_left, pil_top, pil_right, pil_bottom)
                )

                # If image is very large, resize to save memory
                if sprite_image.width > 2048 or sprite_image.height > 2048:
                    sprite_image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

                # Convert to PNG bytes
                buf = io.BytesIO()
                sprite_image.save(buf, format="PNG")
                image_data = buf.getvalue()

                # Clean up
                del sprite_image
                del buf

            except Exception:
                # Texture extraction failed, return without image data
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

        except Exception:
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

    def _extract_atlas_sprite(
        self,
        sprite_name: str,
        atlas_info: Any,
        textures_by_pathid: Dict[int, Any],
        bundle_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a sprite from a sprite atlas.

        Args:
            sprite_name: Name of the sprite
            atlas_info: SpriteAtlasInfo with texture reference and coordinates
            textures_by_pathid: Cache of loaded textures
            bundle_name: Name of the bundle

        Returns:
            Dictionary with sprite metadata and cropped image data
        """
        # Get the atlas texture
        atlas_tex = textures_by_pathid.get(atlas_info.texture_path_id)
        if not atlas_tex:
            # Texture not found, return sprite without image
            return {
                "name": sprite_name,
                "bundle": bundle_name,
                "has_vertex_data": False,
                "width": atlas_info.rect_width,
                "height": atlas_info.rect_height,
                "image_data": None,
                "atlas": atlas_info.atlas_name,
                **self._create_default_status(),
            }

        try:
            # Get the atlas as a PIL image
            atlas_image = atlas_tex.image
            if not atlas_image:
                return None

            # atlas_width = atlas_image.width
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
            sprite_image = atlas_image.crop((pil_left, pil_top, pil_right, pil_bottom))

            # Convert to PNG bytes
            buf = io.BytesIO()
            sprite_image.save(buf, format="PNG")
            image_data = buf.getvalue()

            return {
                "name": sprite_name,
                "bundle": bundle_name,
                "has_vertex_data": False,
                "width": rect_width,
                "height": rect_height,
                "image_data": image_data,
                "atlas": atlas_info.atlas_name,
                **self._create_default_status(),
            }

        except Exception:
            # Failed to extract image, return sprite metadata without image
            return {
                "name": sprite_name,
                "bundle": bundle_name,
                "has_vertex_data": False,
                "width": atlas_info.rect_width,
                "height": atlas_info.rect_height,
                "image_data": None,
                "atlas": atlas_info.atlas_name,
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
