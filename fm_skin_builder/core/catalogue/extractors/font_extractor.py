"""
Font Extractor

Extracts font assets from Unity bundles.
"""

from __future__ import annotations
from pathlib import Path
from typing import List
import UnityPy

from .base import BaseAssetExtractor
from ..models import Font


class FontExtractor(BaseAssetExtractor):
    """Extracts font assets from bundles."""

    def extract_from_bundle(self, bundle_path: Path) -> List[Font]:
        """
        Extract fonts from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of Font model instances
        """
        env = UnityPy.load(str(bundle_path))
        bundle_name = bundle_path.name

        fonts = []

        for obj in env.objects:
            if obj.type.name != "Font":
                continue

            try:
                data = obj.read()
            except Exception:
                continue

            name = self._get_asset_name(data)
            if not name:
                continue

            # Generate tags from font name
            tags = self._generate_tags_from_font_name(name)

            font = Font(
                name=name,
                bundles=[bundle_name],
                tags=tags,
                **self._create_default_status(),
            )
            fonts.append(font)

        return fonts

    def _generate_tags_from_font_name(self, name: str) -> List[str]:
        """
        Generate tags from font name.

        Args:
            name: Font name (e.g., "Roboto-Regular")

        Returns:
            List of tags
        """
        tags = ["font"]

        # Split by common delimiters
        import re
        parts = re.split(r'[-_\s]', name.lower())

        for part in parts:
            if len(part) > 2:
                tags.append(part)

        return tags
