"""
VTA Header Parser - Extract metadata from Unity VisualTreeAsset binary

Parses the VTA header structure to extract:
- Fixed header (72 bytes)
- Template references section
- Array offsets for visual elements and template instances
"""

from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TemplateReference:
    """Single template reference metadata."""

    name: str
    guid: str


@dataclass
class VTAHeader:
    """Represents parsed VTA header with all metadata."""

    # Fixed header (0-72 bytes) - preserved verbatim
    fixed_header: bytes

    # Template references section
    template_refs: List[TemplateReference]

    # Calculated offsets
    visual_array_offset: int
    template_array_offset: int

    # TypeTree metadata (extracted from original)
    visual_typetree: bytes  # 40 bytes
    template_typetree: bytes  # 12 bytes


def parse_vta_header(raw_data: bytes) -> VTAHeader:
    """
    Parse VTA header from binary data.

    Args:
        raw_data: Complete VTA binary data

    Returns:
        VTAHeader with all metadata extracted
    """
    # Extract fixed header (0-72)
    fixed_header = raw_data[0:72]

    # Parse template references section (starts at offset 72)
    template_refs, template_refs_end = _parse_template_references(raw_data, 72)

    # Visual array starts after template references
    visual_array_offset = template_refs_end

    # Extract visual TypeTree metadata (40 bytes after count at visual_array_offset)
    visual_typetree_offset = visual_array_offset + 4
    visual_typetree = raw_data[visual_typetree_offset : visual_typetree_offset + 40]

    # Visual elements data starts after count + TypeTree
    visual_data_start = visual_array_offset + 4 + 40

    # Find template array (search for template count)
    # This is harder - need to skip past all visual elements
    # For now, we'll find it by searching for the template count value
    template_array_offset = _find_template_array_offset(
        raw_data, visual_data_start, template_refs
    )

    # Extract template TypeTree metadata (12 bytes after count)
    template_typetree_offset = template_array_offset + 4
    template_typetree = raw_data[
        template_typetree_offset : template_typetree_offset + 12
    ]

    return VTAHeader(
        fixed_header=fixed_header,
        template_refs=template_refs,
        visual_array_offset=visual_array_offset,
        template_array_offset=template_array_offset,
        visual_typetree=visual_typetree,
        template_typetree=template_typetree,
    )


def _parse_template_references(
    raw_data: bytes, start_offset: int
) -> Tuple[List[TemplateReference], int]:
    """
    Parse template references section.

    Args:
        raw_data: Complete binary data
        start_offset: Where template refs section starts (usually 72)

    Returns:
        Tuple of (list of template references, offset where section ends)
    """
    pos = start_offset

    # Read count of unique template references
    template_count = struct.unpack_from("<i", raw_data, pos)[0]
    pos += 4

    templates = []

    for _ in range(template_count):
        # Track where this template starts (for padding calculation)
        template_start = pos

        # Read template name
        name_len = struct.unpack_from("<i", raw_data, pos)[0]
        pos += 4

        name = raw_data[pos : pos + name_len].decode("utf-8")
        pos += name_len

        # After name: align to 4-byte boundary (if needed)
        if name_len % 4 != 0:
            # Add null terminator + padding to reach alignment
            pos += 1  # null terminator
            if pos % 4 != 0:
                pos += 4 - (pos % 4)

        # Skip 4-byte separator block (always 0x20 0x00 0x00 0x00)
        pos += 4

        # GUID is stored as 32-byte ASCII hex string (no length prefix!)
        guid = raw_data[pos : pos + 32].decode("ascii")
        pos += 32 + 1  # +1 for null terminator

        # Align to 4-byte boundary
        if pos % 4 != 0:
            pos += 4 - (pos % 4)

        # Padding: aligns total template size to multiples of 12 bytes
        # Formula: padding = 12 - (size_before_padding % 12)
        size_before_padding = pos - template_start
        padding = 12 - (size_before_padding % 12)
        pos += padding

        templates.append(TemplateReference(name=name, guid=guid))

    return templates, pos


def _find_template_array_offset(
    raw_data: bytes, search_start: int, template_refs: List[TemplateReference]
) -> int:
    """
    Find where template array starts by looking for TypeTree metadata.

    Template array has 12-byte TypeTree that's all zeros, which is distinctive.

    Args:
        raw_data: Complete binary data
        search_start: Where to start searching (after visual elements)
        template_refs: Template references (for validation)

    Returns:
        Offset where template array starts (count field)
    """
    # Search for pattern: count (small number) + 12 bytes of zeros
    # This is the template array signature

    pos = search_start

    # Search in reasonable range (visual elements shouldn't be more than 50KB)
    max_search = min(search_start + 100000, len(raw_data) - 16)

    while pos < max_search:
        # Try to read a potential count
        if pos + 16 <= len(raw_data):
            potential_count = struct.unpack_from("<i", raw_data, pos)[0]

            # Check if this looks like a template count (reasonable range)
            if 0 < potential_count < 100:
                # Check if next 12 bytes are zeros (template TypeTree)
                next_12 = raw_data[pos + 4 : pos + 16]
                if next_12 == b"\x00" * 12:
                    # This looks like template array!
                    return pos

        pos += 4

    # Fallback: couldn't find it
    raise ValueError("Could not locate template array in binary data")


def serialize_template_references(template_refs: List[TemplateReference]) -> bytes:
    """
    Serialize template references section back to binary.

    Args:
        template_refs: List of template references to serialize

    Returns:
        Binary data for template references section
    """
    data = bytearray()

    # Write count
    data.extend(struct.pack("<i", len(template_refs)))

    for ref in template_refs:
        # Track where this template starts (for padding calculation)
        template_start = len(data)

        # Write name
        name_bytes = ref.name.encode("utf-8")
        data.extend(struct.pack("<i", len(name_bytes)))
        data.extend(name_bytes)

        # After name: align to 4-byte boundary (if needed)
        if len(name_bytes) % 4 != 0:
            # Add null terminator + padding to reach alignment
            data.append(0)  # null terminator
            while len(data) % 4 != 0:
                data.append(0)

        # Write 4-byte separator block (always 0x20 0x00 0x00 0x00)
        data.extend(b"\x20\x00\x00\x00")

        # Write GUID (always 32 bytes, no length prefix!)
        guid_bytes = ref.guid.encode("ascii")
        if len(guid_bytes) != 32:
            raise ValueError(
                f"GUID must be 32 bytes, got {len(guid_bytes)}: {ref.guid}"
            )
        data.extend(guid_bytes)
        data.append(0)  # null terminator

        # Align to 4-byte boundary
        while len(data) % 4 != 0:
            data.append(0)

        # Padding: aligns total template size to multiples of 12 bytes
        # Formula: padding = 12 - (size_before_padding % 12)
        size_before_padding = len(data) - template_start
        padding = 12 - (size_before_padding % 12)
        data.extend(b"\x00" * padding)

    return bytes(data)
