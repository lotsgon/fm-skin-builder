"""Vector sprite replacement utilities.

This module rebuilds Unity sprite mesh data directly and scales the generated
geometry so it fits the sprite rect and pivot. The helpers here are used when a
skin mapping requests a `type=vector` override – the CLI will extract SVG path
data, construct new vertex/index buffers, and write them back to the sprite.

The regenerated mesh keeps the original SpriteAtlas reference intact, which is
required for Football Manager's SIImage to draw the sprite while still honouring
the custom geometry and colour overrides.
"""

from __future__ import annotations
import struct
import math
from typing import List, Tuple, Optional
import logging

log = logging.getLogger(__name__)


def create_circle_mesh(
    radius: float = 0.5, segments: int = 48
) -> Tuple[List[Tuple[float, float, float]], List[int]]:
    """Create a unit circle mesh centred around the origin.

    The circle is generated with a centre vertex followed by a configurable number of
    segments on the circumference. The returned geometry is intentionally normalised –
    callers are expected to scale it to their desired size.
    """

    segments = max(3, int(segments))
    base_radius = radius if radius > 0 else 0.5

    vertices: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
    for i in range(segments):
        angle = (2.0 * math.pi * i) / segments
        x = base_radius * math.cos(angle)
        y = base_radius * math.sin(angle)
        vertices.append((x, y, 0.0))

    indices: List[int] = []
    for i in range(segments):
        indices.extend((0, i + 1, 1 + ((i + 1) % segments)))

    return vertices, indices


def create_square_mesh(size: float = 0.5) -> Tuple[List[Tuple[float, float, float]], List[int]]:
    """Create a unit square centred at the origin."""

    half = size if size > 0 else 0.5
    vertices: List[Tuple[float, float, float]] = [
        (-half, -half, 0.0),  # bottom-left
        (half, -half, 0.0),  # bottom-right
        (half, half, 0.0),  # top-right
        (-half, half, 0.0),  # top-left
    ]

    indices: List[int] = [0, 1, 2, 0, 2, 3]
    return vertices, indices


def svg_path_to_mesh(
    svg_path: str, *, samples: int = 96
) -> Optional[Tuple[List[Tuple[float, float, float]], List[int]]]:
    """Convert an SVG path into a normalised polygon fan mesh.

    The resulting vertex list is centred around the path centroid so it can be scaled to
    match the target sprite bounds afterwards.
    """

    try:
        from svg.path import parse_path

        path = parse_path(svg_path)
        if path.length(error=1e-3) == 0:
            return None

        steps = max(16, min(512, int(samples)))
        points: List[Tuple[float, float]] = []
        for i in range(steps):
            t = i / steps
            pt = path.point(t)
            points.append((float(pt.real), float(pt.imag)))

        # Ensure the path is closed by appending the final point if necessary
        last_point = path.point(1.0)
        end = (float(last_point.real), float(last_point.imag))
        if not points or (abs(points[0][0] - end[0]) > 1e-5 or abs(points[0][1] - end[1]) > 1e-5):
            points.append(end)

        # Deduplicate consecutive duplicates
        deduped: List[Tuple[float, float]] = []
        for p in points:
            if not deduped or (
                abs(deduped[-1][0] - p[0]) > 1e-5 or abs(deduped[-1][1] - p[1]) > 1e-5
            ):
                deduped.append(p)

        if len(deduped) < 3:
            return None

        # Compute centroid and centre the polygon around (0,0)
        cx = sum(p[0] for p in deduped) / len(deduped)
        cy = sum(p[1] for p in deduped) / len(deduped)

        vertices: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
        for x, y in deduped:
            vertices.append((x - cx, y - cy, 0.0))

        indices: List[int] = []
        for i in range(1, len(vertices) - 1):
            indices.extend((0, i, i + 1))

        # Close the fan
        indices.extend((0, len(vertices) - 1, 1))

        return vertices, indices

    except ImportError:
        log.warning(
            "[VECTOR] svg.path library not available. Install 'svg.path' to convert SVG paths."
        )
        return None
    except Exception as e:
        log.warning(f"[VECTOR] Failed to parse SVG path: {e}")
        return None


def _pack_vertex_data(positions: List[Tuple[float, float, float]]) -> bytes:
    """Pack position + empty UV streams to the layout Unity expects for sprites."""

    if not positions:
        return b""

    buf = bytearray()
    for x, y, z in positions:
        buf.extend(struct.pack("<fff", float(x), float(y), float(z)))

    # Append zeroed UV pairs (2 floats per vertex)
    buf.extend(b"\x00" * (len(positions) * 8))
    return bytes(buf)


def _fit_positions_to_sprite(
    positions: List[Tuple[float, float, float]],
    width_units: float,
    height_units: float,
    pivot_x: float,
    pivot_y: float,
    *,
    scale_override: float = 1.0,
) -> List[Tuple[float, float, float]]:
    if not positions:
        return positions

    min_x = min(x for x, _, _ in positions)
    max_x = max(x for x, _, _ in positions)
    min_y = min(y for _, y, _ in positions)
    max_y = max(y for _, y, _ in positions)

    mesh_width = max_x - min_x
    mesh_height = max_y - min_y
    if mesh_width <= 1e-6 or mesh_height <= 1e-6:
        return positions

    width_units = max(width_units, 1e-6)
    height_units = max(height_units, 1e-6)

    scale_x = width_units / mesh_width
    scale_y = height_units / mesh_height
    if scale_override < 0:
        log.warning("Negative scale_override (%f) is invalid; using 1e-6 instead.", scale_override)
        scale_override_used = 1e-6
    else:
        scale_override_used = scale_override
    uniform_scale = min(scale_x, scale_y) * scale_override_used

    center_x = (min_x + max_x) * 0.5
    center_y = (min_y + max_y) * 0.5

    pivot_offset_x = (0.5 - pivot_x) * width_units
    pivot_offset_y = (0.5 - pivot_y) * height_units

    fitted: List[Tuple[float, float, float]] = []
    for x, y, z in positions:
        sx = (x - center_x) * uniform_scale + pivot_offset_x
        sy = (y - center_y) * uniform_scale + pivot_offset_y
        fitted.append((sx, sy, z * uniform_scale))

    return fitted


def replace_vector_sprite(
    sprite_obj, shape: str = "circle", color: Optional[Tuple[int, int, int, int]] = None, **kwargs
):
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
        scale_override = float(kwargs.get("scale", 1.0))

        if shape == "circle":
            segments = kwargs.get("segments", 48)
            vertices, indices = create_circle_mesh(segments=int(segments))
        elif shape == "square":
            vertices, indices = create_square_mesh()
        elif shape == "custom" and "svg_path" in kwargs:
            mesh = svg_path_to_mesh(kwargs["svg_path"])
            if mesh is None:
                return False
            vertices, indices = mesh
        else:
            log.warning(f"[VECTOR] Unknown shape '{shape}' or missing parameters")
            return False

        # Update the sprite's render data
        rd = sprite_obj.m_RD

        rect = sprite_obj.m_Rect
        pixels_to_units = float(sprite_obj.m_PixelsToUnits or 100.0)
        width_units = (rect.width or 0.0) / pixels_to_units
        height_units = (rect.height or 0.0) / pixels_to_units
        if width_units <= 0 or height_units <= 0:
            log.warning("[VECTOR] Sprite '%s' has zero-sized rect; skipping", sprite_obj.m_Name)
            return False

        pivot = getattr(sprite_obj, "m_Pivot", None)
        pivot_x = getattr(pivot, "x", 0.5)
        pivot_y = getattr(pivot, "y", 0.5)

        fitted_vertices = _fit_positions_to_sprite(
            vertices,
            width_units,
            height_units,
            pivot_x,
            pivot_y,
            scale_override=scale_override,
        )

        vertex_count = len(fitted_vertices)
        if vertex_count < 3:
            log.warning("[VECTOR] Mesh for '%s' has insufficient vertices", sprite_obj.m_Name)
            return False

        vertex_data = _pack_vertex_data(fitted_vertices)
        if not indices:
            log.warning("[VECTOR] Mesh for '%s' produced no indices", sprite_obj.m_Name)
            return False

        index_bytes = bytearray()
        for idx in indices:
            index_bytes.extend(struct.pack("<H", int(idx)))
        index_data = bytes(index_bytes)

        index_count = len(indices)

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
            if hasattr(submesh, "triangleCount"):
                try:
                    submesh.triangleCount = index_count // 3
                except Exception as e:
                    log.warning(f"[VECTOR] Failed to set submesh.triangleCount: {e}")
            if getattr(submesh, "localAABB", None) is not None:
                try:
                    from UnityPy.classes.math import Vector3f

                    half_width = width_units * 0.5
                    half_height = height_units * 0.5
                    center = Vector3f(
                        (0.5 - pivot_x) * width_units, (0.5 - pivot_y) * height_units, 0.0
                    )
                    extent = Vector3f(half_width, half_height, 0.0)
                    submesh.localAABB.m_Center = center
                    submesh.localAABB.m_Extent = extent
                except Exception as e:
                    log.warning(f"[VECTOR] Failed to set localAABB: {e}")

        # NOTE: We keep the SpriteAtlas reference intact. Even though the sprite references
        # an atlas, the vertex data and mesh should take precedence when rendered.
        # Clearing the reference might cause Unity to fall back to cached textures.

        # Update color if provided
        if color is not None:
            r, g, b, a = color
            # Convert 0-255 to 0-100 range that Unity uses
            rd.uvTransform.x = r / 2.55
            rd.uvTransform.y = g / 2.55
            rd.uvTransform.z = b / 2.55
            rd.uvTransform.w = a / 2.55

        try:
            sprite_obj.m_IsPolygon = True
        except Exception as e:
            log.warning(f"[VECTOR] Failed to set m_IsPolygon: {e}")

        # Save the sprite
        if hasattr(sprite_obj, "save"):
            sprite_obj.save()

        log.debug(
            f"[VECTOR] Replaced sprite with {shape}: {vertex_count} vertices, {index_count} indices"
        )
        return True

    except Exception as e:
        log.warning(f"[VECTOR] Failed to replace vector sprite: {e}")
        return False
