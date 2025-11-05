"""Asset catalog builder - creates searchable cross-reference database.

This extends the CSS/UXML catalog to include all asset types:
- Backgrounds/Textures
- Sprites
- Fonts
- Videos
- And their relationships to CSS/UXML
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import json
import re
from collections import defaultdict

import UnityPy
from .logger import get_logger
from .css_patcher import build_selector_from_parts

log = get_logger(__name__)


class AssetCatalog:
    """Builds a searchable catalog of all assets and their relationships."""

    def __init__(self):
        # Asset inventories
        self.backgrounds: Dict[str, Dict[str, Any]] = {}
        self.sprites: Dict[str, Dict[str, Any]] = {}
        self.fonts: Dict[str, Dict[str, Any]] = {}
        self.videos: Dict[str, Dict[str, Any]] = {}
        self.textures: Dict[str, Dict[str, Any]] = {}

        # Cross-references (will be populated during scan)
        self._asset_references = defaultdict(lambda: defaultdict(set))

    def scan_bundle(self, bundle_path: Path, bundle_name: str = "") -> None:
        """Scan a bundle and populate catalog entries."""
        log.info(f"Cataloging assets in: {bundle_path.name}")

        try:
            env = UnityPy.load(str(bundle_path))
        except Exception as e:
            log.error(f"Failed to load bundle {bundle_path}: {e}")
            return

        name = bundle_name or bundle_path.stem

        # Scan all objects
        for obj in env.objects:
            try:
                tname = obj.type.name

                if tname == "Texture2D":
                    self._catalog_texture(obj, name)
                elif tname == "Sprite":
                    self._catalog_sprite(obj, name)
                elif tname == "Font":
                    self._catalog_font(obj, name)
                elif tname in ("VideoClip", "MovieTexture"):
                    self._catalog_video(obj, name)
            except Exception as e:
                log.debug(f"Failed to catalog object in {bundle_path}: {e}")

        # Cleanup
        try:
            del env
        except Exception:
            pass

        log.info(
            f"  ✓ {len(self.textures)} textures, {len(self.sprites)} sprites, {len(self.fonts)} fonts")

    def _catalog_texture(self, obj, bundle: str) -> None:
        """Catalog Texture2D assets (backgrounds, UI elements)."""
        try:
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)

            if not name:
                return

            width = getattr(data, "m_Width", None) or getattr(
                data, "width", None)
            height = getattr(data, "m_Height", None) or getattr(
                data, "height", None)
            texture_format = getattr(data, "m_TextureFormat", None)

            # Categorize as background if large enough
            is_background = False
            if width and height:
                is_background = width >= 512 or height >= 512

            entry = {
                "type": "Texture2D",
                "bundle": bundle,
                "dimensions": {"width": width, "height": height},
                "format": texture_format,
                "is_background": is_background,
                "path_id": obj.path_id,
                "referenced_in_uxml": [],
                "referenced_in_css": []
            }

            # Store in appropriate category
            if is_background:
                self.backgrounds[name] = entry
            else:
                self.textures[name] = entry

        except Exception as e:
            log.debug(f"Failed to catalog texture: {e}")

    def _catalog_sprite(self, obj, bundle: str) -> None:
        """Catalog Sprite assets."""
        try:
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)

            if not name:
                return

            # Get sprite dimensions
            rect = getattr(data, "m_Rect", None)
            width = height = None
            if rect:
                width = getattr(rect, "width", None)
                height = getattr(rect, "height", None)

            self.sprites[name] = {
                "bundle": bundle,
                "dimensions": {"width": width, "height": height} if width else None,
                "path_id": obj.path_id,
                "referenced_in_uxml": [],
                "referenced_in_css": []
            }

        except Exception as e:
            log.debug(f"Failed to catalog sprite: {e}")

    def _catalog_font(self, obj, bundle: str) -> None:
        """Catalog Font assets."""
        try:
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)

            if not name:
                return

            font_size = getattr(data, "m_FontSize", None)
            line_spacing = getattr(data, "m_LineSpacing", None)

            self.fonts[name] = {
                "bundle": bundle,
                "size": font_size,
                "line_spacing": line_spacing,
                "path_id": obj.path_id,
                "used_in_css": [],
                "used_in_uxml": []
            }

        except Exception as e:
            log.debug(f"Failed to catalog font: {e}")

    def _catalog_video(self, obj, bundle: str) -> None:
        """Catalog VideoClip assets."""
        try:
            data = obj.read()
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)

            if not name:
                return

            self.videos[name] = {
                "bundle": bundle,
                "path_id": obj.path_id,
                "referenced_in_uxml": []
            }

        except Exception as e:
            log.debug(f"Failed to catalog video: {e}")

    def cross_reference_with_uxml(self, uxml_catalog: Dict[str, Dict[str, Any]]) -> None:
        """Build cross-references between assets and UXML files."""
        log.info("Building asset → UXML cross-references...")

        for uxml_name, uxml_info in uxml_catalog.items():
            # Get UXML content if available
            uxml_content = uxml_info.get("content", "")

            if not uxml_content:
                continue

            # Search for asset references by name
            # Backgrounds
            for bg_name in self.backgrounds.keys():
                if bg_name in uxml_content:
                    self.backgrounds[bg_name]["referenced_in_uxml"].append(
                        uxml_name)

            # Textures
            for tex_name in self.textures.keys():
                if tex_name in uxml_content:
                    self.textures[tex_name]["referenced_in_uxml"].append(
                        uxml_name)

            # Sprites
            for sprite_name in self.sprites.keys():
                if sprite_name in uxml_content:
                    self.sprites[sprite_name]["referenced_in_uxml"].append(
                        uxml_name)

            # Fonts
            for font_name in self.fonts.keys():
                if font_name in uxml_content:
                    self.fonts[font_name]["used_in_uxml"].append(uxml_name)

            # Videos
            for video_name in self.videos.keys():
                if video_name in uxml_content:
                    self.videos[video_name]["referenced_in_uxml"].append(
                        uxml_name)

        log.info("  ✓ Cross-reference complete")

    def cross_reference_with_css(self, css_catalog: Dict[str, Dict[str, Any]]) -> None:
        """Build cross-references between assets and CSS stylesheets."""
        log.info("Building asset → CSS cross-references...")

        for sheet_name, sheet_info in css_catalog.items():
            # Get CSS content if available
            css_content = sheet_info.get("content", "")

            if not css_content:
                continue

            # Search for asset references in CSS
            # Backgrounds (often in background-image properties)
            for bg_name in self.backgrounds.keys():
                if bg_name in css_content:
                    self.backgrounds[bg_name]["referenced_in_css"].append(
                        sheet_name)

            # Textures
            for tex_name in self.textures.keys():
                if tex_name in css_content:
                    self.textures[tex_name]["referenced_in_css"].append(
                        sheet_name)

            # Sprites
            for sprite_name in self.sprites.keys():
                if sprite_name in css_content:
                    self.sprites[sprite_name]["referenced_in_css"].append(
                        sheet_name)

            # Fonts (font-family, -unity-font, etc)
            for font_name in self.fonts.keys():
                if font_name in css_content:
                    self.fonts[font_name]["used_in_css"].append(sheet_name)

        log.info("  ✓ Cross-reference complete")

    def to_dict(self) -> Dict[str, Any]:
        """Export catalog as dictionary for JSON serialization."""
        return {
            "backgrounds": self.backgrounds,
            "textures": self.textures,
            "sprites": self.sprites,
            "fonts": self.fonts,
            "videos": self.videos
        }

    def merge_into_catalog(self, catalog: Dict[str, Any]) -> None:
        """Merge asset data into existing CSS/UXML catalog."""
        catalog["backgrounds"] = self.backgrounds
        catalog["textures"] = self.textures
        catalog["sprites"] = self.sprites
        catalog["fonts"] = self.fonts
        catalog["videos"] = self.videos
