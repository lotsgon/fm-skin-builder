"""
Font Swap Service

Handles font replacement in Unity bundles by discovering font files
in the skin directory and swapping them with game fonts.

IMPORTANT: Font format (OTF vs TTF) must match the original. Unity
expects specific internal font tables:
- OTF fonts use CFF (Compact Font Format) tables
- TTF fonts use glyf (glyph data) tables
Renaming .ttf to .otf or vice versa will NOT work.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Literal

from .context import BundleContext, PatchReport

logger = logging.getLogger(__name__)

FontFormat = Literal["TTF", "OTF", "UNKNOWN"]


@dataclass
class FontSwapOptions:
    """Options for font swapping service."""

    includes: Sequence[str]
    dry_run: bool = False


@dataclass
class FontSwapResult:
    """Result of font swap operation."""

    replaced_count: int
    discovered_fonts: Dict[str, Path]
    skipped_fonts: Dict[str, str]  # font_name -> reason


class FontSwapService:
    """
    Service for replacing fonts in Unity bundles.

    Discovers fonts in assets/fonts/ directory and replaces matching fonts
    in game bundles. Supports both stem-based matching and explicit mapping.

    CRITICAL: Font format (OTF vs TTF) must match the original Unity Font asset.
    The service validates this using magic bytes to prevent silent failures.
    """

    SUPPORTED_EXTENSIONS = {".ttf", ".otf"}
    MAX_SIZE_MB = 50
    WARN_SIZE_MB = 5

    # Font format magic bytes
    TTF_MAGIC = [
        b"\x00\x01\x00\x00",  # TrueType 1.0
        b"true",              # TrueType (Mac)
    ]
    OTF_MAGIC = b"OTTO"  # OpenType with CFF

    def __init__(self, options: FontSwapOptions):
        self.options = options
        self._font_mapping: Optional[Dict[str, Path]] = None
        self._original_font_formats: Dict[str, FontFormat] = {}  # Cache original formats

    def apply(
        self,
        bundle: BundleContext,
        skin_dir: Path,
        report: PatchReport,
    ) -> FontSwapResult:
        """
        Apply font replacements to a bundle.

        Args:
            bundle: Bundle context to modify
            skin_dir: Skin directory containing assets/fonts/
            report: Patch report to update

        Returns:
            FontSwapResult with replacement counts and discovered fonts
        """
        if not self._should_swap():
            return FontSwapResult(0, {}, {})

        # Discover fonts if not already done
        if self._font_mapping is None:
            self._font_mapping = self._discover_fonts(skin_dir)

        if not self._font_mapping:
            logger.debug("No fonts discovered in skin directory")
            return FontSwapResult(0, {}, {})

        # Load bundle
        bundle.load()

        # Attempt to replace each font
        replaced_count = 0
        skipped_fonts: Dict[str, str] = {}

        for font_name, font_file in self._font_mapping.items():
            # Get original format if we've seen this font before
            original_format = self._original_font_formats.get(font_name)

            # Validate font file before attempting replacement
            validation_error = self._validate_font_file(font_file, original_format)
            if validation_error:
                skipped_fonts[font_name] = validation_error
                logger.warning(f"Skipping font '{font_name}': {validation_error}")
                continue

            # Attempt replacement
            if self.options.dry_run:
                logger.info(f"[DRY-RUN] Would replace font: {font_name}")
                replaced_count += 1
            else:
                try:
                    success = self._replace_font_in_bundle(
                        bundle, font_name, font_file
                    )
                    if success:
                        replaced_count += 1
                        logger.info(
                            f"✓ Replaced font: {font_name} ({font_file.name})"
                        )
                    else:
                        skipped_fonts[font_name] = "Font not found in bundle"
                        logger.debug(f"Font '{font_name}' not found in bundle")
                except Exception as e:
                    skipped_fonts[font_name] = f"Error: {str(e)}"
                    logger.error(f"Failed to replace font '{font_name}': {e}")

        # Update report
        if replaced_count > 0:
            report.font_replacements = replaced_count
            if not self.options.dry_run:
                bundle.mark_dirty()

        return FontSwapResult(replaced_count, self._font_mapping, skipped_fonts)

    def _should_swap(self) -> bool:
        """Check if font swapping should be performed based on includes."""
        includes_lower = {inc.lower() for inc in self.options.includes}
        return any(
            token in includes_lower
            for token in {"fonts", "assets/fonts", "all"}
        )

    def _discover_fonts(self, skin_dir: Path) -> Dict[str, Path]:
        """
        Discover fonts in the skin directory.

        Supports two discovery methods:
        1. Stem-based matching: FontName.ttf -> replaces "FontName"
        2. Explicit mapping: font-mapping.json

        Args:
            skin_dir: Skin directory path

        Returns:
            Dictionary mapping font names to font file paths
        """
        font_mapping: Dict[str, Path] = {}

        # Check for explicit mapping file first
        mapping_file = skin_dir / "assets" / "fonts" / "font-mapping.json"
        if mapping_file.exists():
            try:
                with mapping_file.open("r", encoding="utf-8") as f:
                    explicit_mapping = json.load(f)

                # Handle both simple and nested formats
                if "replacements" in explicit_mapping:
                    replacements = explicit_mapping["replacements"]
                else:
                    replacements = explicit_mapping

                for font_name, font_path_str in replacements.items():
                    font_path = skin_dir / "assets" / "fonts" / font_path_str
                    if font_path.exists():
                        font_mapping[font_name] = font_path
                        logger.debug(
                            f"Mapped font '{font_name}' -> {font_path.name} (explicit)"
                        )
                    else:
                        logger.warning(
                            f"Font mapping references non-existent file: {font_path}"
                        )

                logger.info(f"Loaded {len(font_mapping)} fonts from mapping file")
                return font_mapping
            except Exception as e:
                logger.warning(f"Failed to load font mapping file: {e}")

        # Fall back to stem-based discovery
        fonts_dir = skin_dir / "assets" / "fonts"
        if not fonts_dir.exists():
            logger.debug(f"Fonts directory not found: {fonts_dir}")
            return {}

        for font_file in fonts_dir.iterdir():
            if not font_file.is_file():
                continue

            # Check if file has supported extension
            if font_file.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            # Use stem as font name (FontName.ttf -> "FontName")
            font_name = font_file.stem
            font_mapping[font_name] = font_file
            logger.debug(f"Discovered font '{font_name}' -> {font_file.name}")

        if font_mapping:
            logger.info(
                f"Discovered {len(font_mapping)} fonts in {fonts_dir.relative_to(skin_dir)}"
            )

        return font_mapping

    def _validate_font_file(
        self, font_file: Path, original_format: Optional[FontFormat] = None
    ) -> Optional[str]:
        """
        Validate a font file.

        Args:
            font_file: Path to font file
            original_format: Expected format from original Unity Font (if known)

        Returns:
            Error message if validation fails, None if valid
        """
        # Check existence
        if not font_file.exists():
            return f"File not found: {font_file}"

        # Check readability
        if not font_file.is_file():
            return f"Not a file: {font_file}"

        # Check extension
        if font_file.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return f"Unsupported format: {font_file.suffix} (supported: {', '.join(self.SUPPORTED_EXTENSIONS)})"

        # Check size
        size_mb = font_file.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_SIZE_MB:
            return f"File too large: {size_mb:.1f} MB (max: {self.MAX_SIZE_MB} MB)"

        if size_mb > self.WARN_SIZE_MB:
            logger.warning(
                f"Large font file: {font_file.name} ({size_mb:.1f} MB) - consider optimizing"
            )

        # Detect actual format from magic bytes
        replacement_format = self._detect_font_format_from_file(font_file)
        if replacement_format == "UNKNOWN":
            return f"Unable to detect font format (invalid magic bytes)"

        # Validate format matches original if we know it
        if original_format and original_format != "UNKNOWN":
            if replacement_format != original_format:
                return (
                    f"Format mismatch: original is {original_format}, "
                    f"replacement is {replacement_format}. "
                    f"Unity expects matching formats (OTF→OTF, TTF→TTF)"
                )

        return None

    def _detect_font_format_from_bytes(self, font_bytes: bytes) -> FontFormat:
        """
        Detect font format from magic bytes.

        Args:
            font_bytes: Font file bytes

        Returns:
            "TTF", "OTF", or "UNKNOWN"
        """
        if len(font_bytes) < 4:
            return "UNKNOWN"

        # Check first 4 bytes for magic
        header = font_bytes[:4]

        # OTF check (OpenType with CFF)
        if header == self.OTF_MAGIC:
            return "OTF"

        # TTF checks
        for ttf_magic in self.TTF_MAGIC:
            if header == ttf_magic:
                return "TTF"

        return "UNKNOWN"

    def _detect_font_format_from_file(self, font_file: Path) -> FontFormat:
        """
        Detect font format from file.

        Args:
            font_file: Path to font file

        Returns:
            "TTF", "OTF", or "UNKNOWN"
        """
        try:
            with font_file.open("rb") as f:
                header = f.read(4)
            return self._detect_font_format_from_bytes(header)
        except Exception as e:
            logger.debug(f"Failed to read font file header: {e}")
            return "UNKNOWN"

    def _replace_font_in_bundle(
        self, bundle: BundleContext, font_name: str, font_file: Path
    ) -> bool:
        """
        Replace a font in the bundle using UABEA-style logic.

        This mimics what UABEA's "Import .ttf/.otf" plugin does:
        1. Find the Font object by name (m_Name)
        2. Deserialize to Python object (obj.read())
        3. Replace m_FontData with new font bytes
        4. Keep m_Name unchanged (so USS/UXML refs work)
        5. Reserialize (obj.save_typetree) to preserve Unity structure

        Args:
            bundle: Bundle context
            font_name: Name of font to replace
            font_file: Path to replacement font file

        Returns:
            True if font was replaced, False if not found
        """
        replaced = False

        for obj in bundle.env.objects:
            if obj.type.name != "Font":
                continue

            try:
                data = obj.read()
            except Exception as e:
                logger.debug(f"Failed to read font object: {e}")
                continue

            obj_name = getattr(data, "m_Name", None)
            if obj_name != font_name:
                continue

            # Extract and cache original font format
            original_bytes = getattr(data, "m_FontData", b"")
            original_format = self._detect_font_format_from_bytes(original_bytes)
            if original_format != "UNKNOWN":
                self._original_font_formats[font_name] = original_format
                logger.debug(f"Original font '{font_name}' format: {original_format}")

            # Read new font data
            try:
                font_bytes = font_file.read_bytes()
            except Exception as e:
                logger.error(f"Failed to read font file {font_file}: {e}")
                return False

            # Validate format compatibility
            replacement_format = self._detect_font_format_from_bytes(font_bytes)
            if original_format != "UNKNOWN" and replacement_format != original_format:
                logger.error(
                    f"❌ Format mismatch for '{font_name}': "
                    f"original is {original_format}, replacement is {replacement_format}. "
                    f"Unity expects matching formats. Skipping."
                )
                return False

            # Replace font data (keep m_Name unchanged!)
            try:
                data.m_FontData = font_bytes
                obj.save_typetree(data)  # Critical: reserialize to Unity format
                logger.debug(
                    f"Replaced font data for '{font_name}' "
                    f"({len(font_bytes)} bytes, format: {replacement_format})"
                )
                replaced = True
            except Exception as e:
                logger.error(f"Failed to save font data: {e}")
                return False

        return replaced
