"""
Color Search

LAB color space conversion and perceptual similarity search.

Since colormath is not available, we implement a simple RGB to LAB conversion.
"""

from __future__ import annotations
from typing import List, Dict, Tuple
import math


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color to RGB.

    Args:
        hex_color: Hex color string (e.g., "#1976d2")

    Returns:
        Tuple of (r, g, b) in range 0-255
    """
    hex_color = hex_color.lstrip('#')

    # Handle 3-character hex codes
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])

    # Take first 6 characters (ignore alpha if present)
    hex_color = hex_color[:6]

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return (r, g, b)


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB to LAB color space.

    Simplified conversion for perceptual color comparison.

    Args:
        r, g, b: RGB values (0-255)

    Returns:
        Tuple of (L, a, b) in LAB color space
    """
    # Normalize RGB to 0-1
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    # Apply gamma correction
    r = _gamma_correct(r)
    g = _gamma_correct(g)
    b = _gamma_correct(b)

    # Convert to XYZ color space
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    # Normalize by D65 illuminant
    x = x / 0.95047
    y = y / 1.00000
    z = z / 1.08883

    # Apply LAB transformation
    x = _lab_transform(x)
    y = _lab_transform(y)
    z = _lab_transform(z)

    # Calculate LAB values
    L = (116.0 * y) - 16.0
    a = 500.0 * (x - y)
    b_lab = 200.0 * (y - z)

    return (L, a, b_lab)


def _gamma_correct(value: float) -> float:
    """Apply sRGB gamma correction."""
    if value > 0.04045:
        return math.pow((value + 0.055) / 1.055, 2.4)
    else:
        return value / 12.92


def _lab_transform(value: float) -> float:
    """Apply LAB transformation."""
    if value > 0.008856:
        return math.pow(value, 1.0 / 3.0)
    else:
        return (7.787 * value) + (16.0 / 116.0)


def color_distance(color1: str, color2: str) -> float:
    """
    Calculate perceptual distance between two colors using LAB color space.

    Approximation of Delta E (CIE76).

    Args:
        color1: First hex color (e.g., "#1976d2")
        color2: Second hex color (e.g., "#2196f3")

    Returns:
        Distance value (0 = identical, higher = more different)
    """
    try:
        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)

        L1, a1, b1_lab = rgb_to_lab(r1, g1, b1)
        L2, a2, b2_lab = rgb_to_lab(r2, g2, b2)

        # Delta E (CIE76) - Euclidean distance in LAB space
        delta_L = L1 - L2
        delta_a = a1 - a2
        delta_b = b1_lab - b2_lab

        distance = math.sqrt(delta_L**2 + delta_a**2 + delta_b**2)

        return distance

    except Exception:
        # Fallback to simple RGB distance
        try:
            r1, g1, b1 = hex_to_rgb(color1)
            r2, g2, b2 = hex_to_rgb(color2)
            return math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)
        except Exception:
            return float('inf')


def find_similar_colors(
    target_hex: str,
    color_map: Dict[str, List[str]],
    threshold: float = 20.0
) -> List[str]:
    """
    Find colors similar to target within perceptual distance threshold.

    Args:
        target_hex: Target color (e.g., "#1976d2")
        color_map: Dictionary mapping hex colors to asset names
        threshold: Distance threshold (20.0 = slightly different, 50.0 = noticeably different)

    Returns:
        List of asset names with similar colors
    """
    similar_assets = []

    for hex_color, assets in color_map.items():
        distance = color_distance(target_hex, hex_color)

        if distance <= threshold:
            similar_assets.extend(assets)

    return list(set(similar_assets))  # Remove duplicates
