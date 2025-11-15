"""
Exporter

Exports catalogue data to R2-ready JSON files.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import json

from .models import (
    CatalogueMetadata,
    CSSVariable,
    CSSClass,
    Sprite,
    Texture,
    Font,
)


class CatalogueExporter:
    """Exports catalogue to JSON files for R2."""

    def __init__(self, output_dir: Path, pretty: bool = False):
        """
        Initialize exporter.

        Args:
            output_dir: Output directory
            pretty: Pretty-print JSON
        """
        self.output_dir = output_dir
        self.pretty = pretty

    def export(
        self,
        metadata: CatalogueMetadata,
        css_variables: List[CSSVariable],
        css_classes: List[CSSClass],
        sprites: List[Sprite],
        textures: List[Texture],
        fonts: List[Font],
        search_index: Dict[str, Any],
    ) -> None:
        """
        Export all catalogue data to JSON files.

        Creates structure:
            output_dir/
                metadata.json
                css-variables.json
                css-classes.json
                sprites.json
                textures.json
                fonts.json
                search-index.json
                thumbnails/
                    sprites/
                    textures/

        Args:
            metadata: Catalogue metadata
            css_variables: CSS variables
            css_classes: CSS classes
            sprites: Sprites
            textures: Textures
            fonts: Fonts
            search_index: Search index
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create thumbnails directories
        (self.output_dir / "thumbnails" / "sprites").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "thumbnails" / "textures").mkdir(parents=True, exist_ok=True)

        # Export metadata
        self._write_json(
            self.output_dir / "metadata.json", metadata.model_dump(mode="json")
        )

        # Export CSS variables
        self._write_json(
            self.output_dir / "css-variables.json",
            [v.model_dump(mode="json") for v in css_variables],
        )

        # Export CSS classes
        self._write_json(
            self.output_dir / "css-classes.json",
            [c.model_dump(mode="json") for c in css_classes],
        )

        # Export sprites
        self._write_json(
            self.output_dir / "sprites.json",
            [s.model_dump(mode="json") for s in sprites],
        )

        # Export textures
        self._write_json(
            self.output_dir / "textures.json",
            [t.model_dump(mode="json") for t in textures],
        )

        # Export fonts
        self._write_json(
            self.output_dir / "fonts.json", [f.model_dump(mode="json") for f in fonts]
        )

        # Export search index
        self._write_json(self.output_dir / "search-index.json", search_index)

    def _write_json(self, path: Path, data: Any) -> None:
        """Write data to JSON file."""
        indent = 2 if self.pretty else None
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
