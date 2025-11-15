"""
Search Index Builder

Builds searchable indices for colors and tags across all asset types.
"""

from __future__ import annotations
from typing import Dict, List, Any
from collections import defaultdict

from .models import CSSVariable, CSSClass, Sprite, Texture, Font


class SearchIndexBuilder:
    """Builds search indices for the asset catalogue."""

    def build_index(
        self,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
        sprites: List[Sprite],
        textures: List[Texture],
        fonts: List[Font] = None,
    ) -> Dict[str, Any]:
        """
        Build comprehensive search index.

        Args:
            css_variables: List of CSS variables
            css_classes: List of CSS classes
            sprites: List of sprites
            textures: List of textures
            fonts: List of fonts (optional for backward compatibility)

        Returns:
            Search index dictionary
        """
        fonts = fonts or []

        index = {
            "color_palette": self._build_color_palette(
                css_variables, sprites, textures
            ),
            "tags": self._build_tag_index(
                css_variables, css_classes, sprites, textures
            ),
            "changes": self._build_change_index(
                css_variables, css_classes, sprites, textures, fonts
            ),
        }

        return index

    def _build_color_palette(
        self,
        css_variables: List[CSSVariable],
        sprites: List[Sprite],
        textures: List[Texture],
    ) -> Dict[str, Any]:
        """
        Build color palette index.

        Args:
            css_variables: CSS variables
            sprites: Sprites
            textures: Textures

        Returns:
            Dictionary mapping colors to assets
        """
        palette = {
            "css_variables": defaultdict(list),
            "sprites": defaultdict(list),
            "textures": defaultdict(list),
        }

        # Index CSS variable colors
        for var in css_variables:
            for color in var.colors:
                if color and color.startswith("#"):
                    palette["css_variables"][color].append(var.name)

        # Index sprite colors
        for sprite in sprites:
            for color in sprite.dominant_colors:
                if color and color.startswith("#"):
                    palette["sprites"][color].append(sprite.name)

        # Index texture colors
        for texture in textures:
            for color in texture.dominant_colors:
                if color and color.startswith("#"):
                    palette["textures"][color].append(texture.name)

        # Convert defaultdicts to regular dicts
        return {
            "css_variables": dict(palette["css_variables"]),
            "sprites": dict(palette["sprites"]),
            "textures": dict(palette["textures"]),
        }

    def _build_tag_index(
        self,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
        sprites: List[Sprite],
        textures: List[Texture],
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Build tag index.

        Args:
            css_variables: CSS variables
            css_classes: CSS classes
            sprites: Sprites
            textures: Textures

        Returns:
            Dictionary mapping tags to assets by type
        """
        tag_index = defaultdict(
            lambda: {
                "css_variables": [],
                "css_classes": [],
                "sprites": [],
                "textures": [],
            }
        )

        # Index CSS variable tags (extract from name)
        for var in css_variables:
            # Extract tags from variable name
            name_parts = var.name.lstrip("--").replace("-", "_").split("_")
            for part in name_parts:
                if len(part) > 2:
                    tag_index[part.lower()]["css_variables"].append(var.name)

        # Index CSS class tags
        for cls in css_classes:
            for tag in cls.tags:
                tag_index[tag]["css_classes"].append(cls.name)

        # Index sprite tags
        for sprite in sprites:
            for tag in sprite.tags:
                tag_index[tag]["sprites"].append(sprite.name)

        # Index texture tags
        for texture in textures:
            for tag in texture.tags:
                tag_index[tag]["textures"].append(texture.name)

        return dict(tag_index)

    def _build_change_index(
        self,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
        sprites: List[Sprite],
        textures: List[Texture],
        fonts: List[Font],
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Build change status index for filtering assets by change type.

        Args:
            css_variables: CSS variables
            css_classes: CSS classes
            sprites: Sprites
            textures: Textures
            fonts: Fonts

        Returns:
            Dictionary mapping change statuses to assets by type
        """
        change_index = {
            "new": {
                "css_variables": [],
                "css_classes": [],
                "sprites": [],
                "textures": [],
                "fonts": [],
            },
            "modified": {
                "css_variables": [],
                "css_classes": [],
                "sprites": [],
                "textures": [],
                "fonts": [],
            },
            "unchanged": {
                "css_variables": [],
                "css_classes": [],
                "sprites": [],
                "textures": [],
                "fonts": [],
            },
        }

        # Index CSS variables by change status
        for var in css_variables:
            status = var.change_status or "unchanged"
            if status in change_index:
                change_index[status]["css_variables"].append(var.name)

        # Index CSS classes by change status
        for cls in css_classes:
            status = cls.change_status or "unchanged"
            if status in change_index:
                change_index[status]["css_classes"].append(cls.name)

        # Index sprites by change status
        for sprite in sprites:
            status = sprite.change_status or "unchanged"
            if status in change_index:
                change_index[status]["sprites"].append(sprite.name)

        # Index textures by change status
        for texture in textures:
            status = texture.change_status or "unchanged"
            if status in change_index:
                change_index[status]["textures"].append(texture.name)

        # Index fonts by change status
        for font in fonts:
            status = font.change_status or "unchanged"
            if status in change_index:
                change_index[status]["fonts"].append(font.name)

        return change_index
