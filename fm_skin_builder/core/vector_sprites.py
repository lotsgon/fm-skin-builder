"""Vector sprite replacement - replace mesh-based sprites with custom shapes.

KNOWN LIMITATION (2025-11-04):
While this module successfully modifies vector sprite mesh data (vertices, indices, colors),
the changes do not appear visually in Football Manager. The sprites seem to prioritize
their SpriteAtlas texture reference over the mesh data during rendering. This affects
sprites like kit-squad-outfield and kit-squad-goalkeeper.

Possible causes:
- Sprites reference a SpriteAtlas in an external bundle that takes rendering precedence
- Unity's sprite renderer might use a shader that ignores vertex mesh when texture is present
- Kit sprites might use a specialized rendering path

This module is functional and the data modifications are correct, but visual changes
require further investigation into FM's rendering pipeline.
"""
from __future__ import annotations
import struct
import math
from typing import Tuple, Optional
import logging

log = logging.getLogger(__name__)


def create_circle_mesh(radius: float = 0.64, segments: int = 16) -> Tuple[bytes, bytes, int, int]:
    """Create a circle mesh with vertex and index data.

    Args:
        radius: Circle radius in Unity units (default 0.64 fits in typical 128px sprite)
                Note: Unity coordinates are in units, not pixels. For a 128px sprite with
                PixelsToUnits=100, the coordinate space is approximately ±1.28 units.
        segments: Number of segments (more = smoother circle)

    Returns:
        (vertex_data, index_data, vertex_count, index_count)
    """
    vertices = []

    # Center vertex
    vertices.append((0.0, 0.0, 0.0))

    # Circle vertices
    for i in range(segments):
        angle = (2 * math.pi * i) / segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        vertices.append((x, y, 0.0))

    # Pack vertices as floats (3 per vertex)
    vertex_data = b""
    for x, y, z in vertices:
        vertex_data += struct.pack('<fff', x, y, z)

    # Pad to match Unity's vertex data structure
    # Unity uses two streams - positions and UVs
    # For solid color sprites, we can leave UV stream empty
    # Empty UV data (2 floats per vertex)
    vertex_data += b'\x00' * (len(vertices) * 8)

    # Create index buffer (triangle fan from center)
    indices = []
    for i in range(segments):
        indices.append(0)  # Center
        indices.append(i + 1)
        indices.append(((i + 1) % segments) + 1)

    # Pack indices as unsigned shorts
    index_data = b""
    for idx in indices:
        index_data += struct.pack('<H', idx)

    return vertex_data, index_data, len(vertices), len(indices)


def create_square_mesh(size: float = 0.64) -> Tuple[bytes, bytes, int, int]:
    """Create a square mesh with vertex and index data.

    Args:
        size: Half-size of the square in Unity units (default 0.64 fits in typical 128px sprite)

    Returns:
        (vertex_data, index_data, vertex_count, index_count)
    """
    # Four corners of the square
    vertices = [
        (-size, -size, 0.0),  # Bottom-left
        (size, -size, 0.0),   # Bottom-right
        (size, size, 0.0),    # Top-right
        (-size, size, 0.0),   # Top-left
    ]

    # Pack vertices
    vertex_data = b""
    for x, y, z in vertices:
        vertex_data += struct.pack('<fff', x, y, z)

    # Pad with empty UV data
    vertex_data += b'\x00' * (len(vertices) * 8)

    # Indices for 2 triangles
    indices = [0, 1, 2, 0, 2, 3]

    # Pack indices
    index_data = b""
    for idx in indices:
        index_data += struct.pack('<H', idx)

    return vertex_data, index_data, len(vertices), len(indices)


def svg_path_to_mesh(svg_path: str, scale: float = 1.0) -> Optional[Tuple[bytes, bytes, int, int]]:
    """Convert SVG path data to mesh vertices and indices.

    Args:
        svg_path: SVG path string (e.g., from <path d="..."/>)
        scale: Scale factor to apply

    Returns:
        (vertex_data, index_data, vertex_count, index_count) or None if parsing fails
    """
    try:
        from svg.path import parse_path

        path = parse_path(svg_path)
        vertices = []

        # Sample the path to get vertices
        num_samples = 32
        for i in range(num_samples + 1):
            t = i / num_samples
            point = path.point(t)
            x = point.real * scale
            y = point.imag * scale
            vertices.append((x, y, 0.0))

        # Pack vertices
        vertex_data = b""
        for x, y, z in vertices:
            vertex_data += struct.pack('<fff', x, y, z)

        # Pad with UV data
        vertex_data += b'\x00' * (len(vertices) * 8)

        # Create indices (triangle fan from first vertex)
        indices = []
        for i in range(1, len(vertices) - 1):
            indices.extend([0, i, i + 1])

        # Pack indices
        index_data = b""
        for idx in indices:
            index_data += struct.pack('<H', idx)

        return vertex_data, index_data, len(vertices), len(indices)

    except ImportError:
        log.warning(
            "[VECTOR] svg.path library not available. Install 'svg.path' to convert SVG paths.")
        return None
    except Exception as e:
        log.warning(f"[VECTOR] Failed to parse SVG path: {e}")
        return None


def replace_vector_sprite(sprite_obj, shape: str = "circle", color: Optional[Tuple[int, int, int, int]] = None, **kwargs):
    """Replace a vector sprite's mesh data with a new shape.

    Args:
        sprite_obj: UnityPy Sprite object to modify
        shape: Shape type - "circle", "square", or "custom"
        color: RGBA color tuple (0-255), e.g., (255, 0, 0, 255) for red
        **kwargs: Additional shape-specific parameters
            - radius: for circle (default 64)
            - segments: for circle (default 16)
            - size: for square (default 64)
            - svg_path: for custom SVG path
            - scale: for custom SVG (default 1.0)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate mesh data based on shape
        if shape == "circle":
            radius = kwargs.get("radius", 64.0)
            segments = kwargs.get("segments", 16)
            vertex_data, index_data, vertex_count, index_count = create_circle_mesh(
                radius, segments)
        elif shape == "square":
            size = kwargs.get("size", 64.0)
            vertex_data, index_data, vertex_count, index_count = create_square_mesh(
                size)
        elif shape == "custom" and "svg_path" in kwargs:
            scale = kwargs.get("scale", 1.0)
            result = svg_path_to_mesh(kwargs["svg_path"], scale)
            if result is None:
                return False
            vertex_data, index_data, vertex_count, index_count = result
        else:
            log.warning(
                f"[VECTOR] Unknown shape '{shape}' or missing parameters")
            return False

        # Update the sprite's render data
        rd = sprite_obj.m_RD

        # Update vertex data
        rd.m_VertexData.m_VertexCount = vertex_count
        rd.m_VertexData.m_DataSize = vertex_data

        # Update index buffer
        rd.m_IndexBuffer = index_data

        # Update submesh
        if rd.m_SubMeshes and len(rd.m_SubMeshes) > 0:
            submesh = rd.m_SubMeshes[0]
            submesh.indexCount = index_count
            submesh.vertexCount = vertex_count

        # NOTE: We keep the SpriteAtlas reference intact. Even though the sprite references
        # an atlas, the vertex data and mesh should take precedence when rendered.
        # Clearing the reference might cause Unity to fall back to cached textures.
        # if hasattr(sprite_obj, 'm_SpriteAtlas'):
        #     sprite_obj.m_SpriteAtlas.m_FileID = 0
        #     sprite_obj.m_SpriteAtlas.m_PathID = 0
        #     log.debug("[VECTOR] Cleared SpriteAtlas reference to enable pure vector rendering")

        # Update color if provided
        if color is not None:
            r, g, b, a = color
            # Convert 0-255 to 0-100 range that Unity uses
            rd.uvTransform.x = r / 2.55
            rd.uvTransform.y = g / 2.55
            rd.uvTransform.z = b / 2.55
            rd.uvTransform.w = a / 2.55

        # Save the sprite
        if hasattr(sprite_obj, "save"):
            sprite_obj.save()

        log.debug(
            f"[VECTOR] Replaced sprite with {shape}: {vertex_count} vertices, {index_count} indices")
        return True

    except Exception as e:
        log.warning(f"[VECTOR] Failed to replace vector sprite: {e}")
        return False
