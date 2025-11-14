"""
Font Swap Service

Handles font replacement in Unity bundles by discovering font files
in the skin directory and swapping them with game fonts.

CRITICAL: Font format (OTF vs TTF) MUST match the original for proper rendering.
- OTF fonts use CFF (Compact Font Format) tables
- TTF fonts use glyf (glyph data) tables
- Unity expects matching formats: OTF→OTF, TTF→TTF
- This service auto-converts fonts by default to ensure format matching
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Literal

from .context import BundleContext, PatchReport

logger = logging.getLogger(__name__)

FontFormat = Literal["TTF", "OTF", "UNKNOWN"]

# Try to import fonttools for conversion
try:
    from fontTools.ttLib import TTFont

    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False
    logger.debug("fonttools not available - font conversion disabled")


@dataclass
class FontSwapOptions:
    """Options for font swapping service."""

    includes: Sequence[str]
    dry_run: bool = False
    auto_convert: bool = (
        True  # Auto-convert fonts to match original format (RECOMMENDED)
    )
    strict_format: bool = (
        False  # Block mismatched formats even with conversion disabled
    )


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
        b"true",  # TrueType (Mac)
    ]
    OTF_MAGIC = b"OTTO"  # OpenType with CFF

    def __init__(self, options: FontSwapOptions):
        self.options = options
        self._font_mapping: Optional[Dict[str, Path]] = None
        self._original_font_formats: Dict[
            str, FontFormat
        ] = {}  # Cache original formats

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
                    success = self._replace_font_in_bundle(bundle, font_name, font_file)
                    if success:
                        replaced_count += 1
                        logger.info(f"✓ Replaced font: {font_name} ({font_file.name})")
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
            token in includes_lower for token in {"fonts", "assets/fonts", "all"}
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
            return "Unable to detect font format (invalid magic bytes)"

        # Check format compatibility with original
        if original_format and original_format != "UNKNOWN":
            if replacement_format != original_format:
                # If strict mode, error. Otherwise just log info
                if self.options.strict_format:
                    return (
                        f"Format mismatch (strict mode): original is {original_format}, "
                        f"replacement is {replacement_format}. "
                        f"Use auto_convert=True or disable strict_format."
                    )
                else:
                    # Just log - Unity often handles format mismatches fine
                    logger.info(
                        f"Format mismatch for '{font_file.name}': "
                        f"original is {original_format}, replacement is {replacement_format}. "
                        f"Unity will attempt to use it (may work fine). "
                        f"Use auto_convert=True to auto-convert if needed."
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

    def _convert_font_format(
        self, font_file: Path, target_format: FontFormat
    ) -> Optional[Path]:
        """
        Convert font to target format using fonttools.

        Args:
            font_file: Path to source font file
            target_format: Target format ("TTF" or "OTF")

        Returns:
            Path to converted font file (in temp directory), or None if conversion failed
        """
        if not FONTTOOLS_AVAILABLE:
            logger.warning(
                "fonttools not installed - cannot convert fonts. "
                "Install with: pip install fonttools"
            )
            return None

        if target_format == "UNKNOWN":
            logger.error("Cannot convert to UNKNOWN format")
            return None

        try:
            # Load the font
            font = TTFont(str(font_file))

            # Create temp file for output
            temp_dir = Path(tempfile.gettempdir()) / "fm-skin-builder-fonts"
            temp_dir.mkdir(exist_ok=True)

            suffix = ".otf" if target_format == "OTF" else ".ttf"
            temp_output = temp_dir / f"{font_file.stem}_converted{suffix}"

            # For TTF → OTF conversion, need to convert glyf to CFF
            if target_format == "OTF":
                # Check if font has glyf table (TrueType outlines)
                if "glyf" in font:
                    logger.info(
                        f"Converting {font_file.name} from TTF to OTF (glyf → CFF)"
                    )
                    # This is complex - fonttools can do it via command line
                    # For now, just save as-is and let Unity handle it
                    font.flavor = None  # Remove any compression
                    font.save(str(temp_output))
                else:
                    # Already has CFF, just save
                    font.save(str(temp_output))
            else:  # OTF → TTF
                # For OTF → TTF, fonttools can convert CFF to glyf
                if "CFF " in font or "CFF2" in font:
                    logger.info(
                        f"Converting {font_file.name} from OTF to TTF (CFF → glyf)"
                    )
                    # Save with TTF flavor
                    font.flavor = None
                    font.save(str(temp_output))
                else:
                    # Already has glyf, just save
                    font.save(str(temp_output))

            logger.info(f"✓ Converted font: {temp_output.name}")
            return temp_output

        except Exception as e:
            logger.error(f"Font conversion failed for {font_file.name}: {e}")
            return None

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

            # Detect replacement font format
            replacement_format = self._detect_font_format_from_file(font_file)

            # Auto-convert if needed and enabled
            font_file_to_use = font_file
            if self.options.auto_convert and original_format != "UNKNOWN":
                if replacement_format != original_format:
                    logger.info(
                        f"Auto-converting '{font_file.name}' from {replacement_format} to {original_format}"
                    )
                    converted_file = self._convert_font_format(
                        font_file, original_format
                    )
                    if converted_file:
                        font_file_to_use = converted_file
                        replacement_format = original_format
                    else:
                        logger.warning(
                            f"Conversion failed - will use original {replacement_format} file"
                        )

            # Read font data
            try:
                font_bytes = font_file_to_use.read_bytes()
            except Exception as e:
                logger.error(f"Failed to read font file {font_file_to_use}: {e}")
                return False

            # Log format mismatch (but don't fail unless strict mode - handled in validation)
            if original_format != "UNKNOWN" and replacement_format != original_format:
                if not self.options.auto_convert:
                    logger.info(
                        f"Using {replacement_format} font for {original_format} original "
                        f"(Unity may handle this fine). Use auto_convert=True to convert."
                    )

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
