"""
Color Extractor

Extracts dominant colors from images using K-means clustering.
"""

from __future__ import annotations
from typing import List
import numpy as np
from PIL import Image
from io import BytesIO
import warnings

try:
    from sklearn.cluster import KMeans

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def extract_dominant_colors(image_data: bytes, num_colors: int = 5) -> List[str]:
    """
    Extract dominant colors from an image using K-means clustering.

    Args:
        image_data: Image data as bytes
        num_colors: Number of dominant colors to extract

    Returns:
        List of hex color strings (e.g., ["#1976d2", "#ffffff"])
    """
    if not SKLEARN_AVAILABLE:
        # Fallback: extract basic colors without clustering
        return _extract_simple_colors(image_data, num_colors)

    try:
        # Load image
        img = Image.open(BytesIO(image_data)).convert("RGB")

        # Resize for faster processing
        img = img.resize((150, 150))

        # Convert to numpy array
        pixels = np.array(img).reshape(-1, 3)

        # Remove fully transparent/white/black if too dominant
        # (to avoid watermark colors dominating)

        # K-means clustering
        kmeans = KMeans(
            n_clusters=min(num_colors, len(pixels)), random_state=42, n_init=10
        )

        # Suppress convergence warnings for images with few unique colors
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=Warning, message=".*Number of distinct clusters.*")
            kmeans.fit(pixels)

        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(int)

        # Sort by frequency (cluster size)
        labels = kmeans.labels_
        counts = np.bincount(labels)
        sorted_indices = np.argsort(-counts)
        sorted_colors = [colors[i] for i in sorted_indices]

        # Convert to hex
        hex_colors = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in sorted_colors]

        return hex_colors[:num_colors]

    except Exception:
        return _extract_simple_colors(image_data, num_colors)


def _extract_simple_colors(image_data: bytes, num_colors: int) -> List[str]:
    """
    Fallback color extraction without sklearn.

    Samples pixels at regular intervals.

    Args:
        image_data: Image data as bytes
        num_colors: Number of colors to extract

    Returns:
        List of hex color strings
    """
    try:
        img = Image.open(BytesIO(image_data)).convert("RGB")
        img = img.resize((100, 100))

        pixels = list(img.getdata())

        # Sample evenly distributed pixels
        step = max(1, len(pixels) // num_colors)
        sampled = pixels[::step][:num_colors]

        hex_colors = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in sampled]

        return hex_colors

    except Exception:
        return []


def calculate_brightness(image_data: bytes) -> float:
    """
    Calculate average brightness of an image (0.0 = black, 1.0 = white).

    Used for determining watermark color.

    Args:
        image_data: Image data as bytes

    Returns:
        Brightness value (0.0-1.0)
    """
    try:
        img = Image.open(BytesIO(image_data)).convert("L")  # Convert to grayscale
        img = img.resize((50, 50))  # Small size for speed

        pixels = np.array(img)
        mean_brightness = np.mean(pixels) / 255.0

        return mean_brightness

    except Exception:
        return 0.5  # Default to medium brightness
