"""
Image Processor

Generates thumbnails with adaptive watermarks for asset previews.
"""

from __future__ import annotations
from pathlib import Path
from typing import Tuple
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import cairosvg

from .color_extractor import calculate_brightness


class ImageProcessor:
    """Processes images to create watermarked thumbnails."""

    def __init__(
        self,
        icon_white_path: Path,
        icon_black_path: Path,
        thumbnail_size: int = 256,
        watermark_opacity: float = 0.35,
    ):
        """
        Initialize image processor.

        Args:
            icon_white_path: Path to white SVG icon
            icon_black_path: Path to black SVG icon
            thumbnail_size: Target thumbnail size (square)
            watermark_opacity: Opacity for watermark (0.0-1.0)
        """
        self.icon_white_path = icon_white_path
        self.icon_black_path = icon_black_path
        self.thumbnail_size = thumbnail_size
        self.watermark_opacity = watermark_opacity

    def create_thumbnail(
        self, image_data: bytes, output_path: Path
    ) -> Tuple[int, int]:
        """
        Create a watermarked thumbnail from image data.

        Args:
            image_data: Original image data as bytes
            output_path: Path to save thumbnail (should end in .webp)

        Returns:
            Tuple of (width, height) of original image
        """
        # Load image
        img = Image.open(BytesIO(image_data)).convert('RGBA')
        original_size = img.size

        # Create thumbnail (maintain aspect ratio)
        img.thumbnail((self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS)

        # Apply watermark
        watermarked = self._apply_watermark(img, image_data)

        # Save as WebP
        output_path.parent.mkdir(parents=True, exist_ok=True)
        watermarked.save(output_path, format='WEBP', quality=85)

        return original_size

    def _apply_watermark(self, img: Image.Image, original_data: bytes) -> Image.Image:
        """
        Apply adaptive watermark to image.

        Args:
            img: PIL Image (RGBA)
            original_data: Original image bytes (for brightness calculation)

        Returns:
            Watermarked image
        """
        # Calculate brightness to determine watermark color
        brightness = calculate_brightness(original_data)

        # Choose icon color based on brightness
        if brightness > 0.5:
            # Light background - use black icon
            icon_path = self.icon_black_path
            text_color = (0, 0, 0, int(255 * self.watermark_opacity))
        else:
            # Dark background - use white icon
            icon_path = self.icon_white_path
            text_color = (255, 255, 255, int(255 * self.watermark_opacity))

        # Load and render SVG icon
        icon_size = int(img.width * 0.15)

        try:
            icon_png = cairosvg.svg2png(
                url=str(icon_path),
                output_width=icon_size,
                output_height=icon_size,
            )
            icon = Image.open(BytesIO(icon_png)).convert('RGBA')

            # Apply opacity to icon
            alpha = icon.split()[3]
            alpha = alpha.point(lambda p: int(p * self.watermark_opacity))
            icon.putalpha(alpha)

            # Paste icon at bottom-right
            x = img.width - icon_size - 10
            y = img.height - icon_size - 10
            img.paste(icon, (x, y), icon)

        except Exception:
            # If icon rendering fails, continue without icon
            pass

        # Add text watermark
        try:
            draw = ImageDraw.Draw(img)
            text = "FM Asset Preview"

            # Try to use default font
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

            # Get text size
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # Fallback estimation
                text_width = len(text) * 6
                text_height = 12

            # Center text at bottom
            text_x = (img.width - text_width) // 2
            text_y = img.height - text_height - 10

            draw.text((text_x, text_y), text, fill=text_color, font=font)

        except Exception:
            # If text rendering fails, continue without text
            pass

        return img
