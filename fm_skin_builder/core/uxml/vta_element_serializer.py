"""
VTA Element Serializer - Serialize element arrays into VTA binary format

Handles serialization of:
- Visual elements array (count + TypeTree + element data)
- Template assets array (count + TypeTree + element data)
"""

from __future__ import annotations
import struct
from typing import List
from .uxml_element_parser import UXMLElementBinary


def serialize_visual_elements_array(
    elements: List[UXMLElementBinary], typetree_metadata: bytes
) -> bytes:
    """
    Serialize visual elements array.

    Format:
      count (4 bytes)
      TypeTree metadata (40 bytes) - copied from original
      element data (variable)

    Args:
        elements: List of visual elements to serialize
        typetree_metadata: 40-byte TypeTree metadata from original VTA

    Returns:
        Binary data for complete visual elements array
    """
    data = bytearray()

    # Write count
    data.extend(struct.pack("<i", len(elements)))

    # Write TypeTree metadata (preserve original)
    if len(typetree_metadata) != 40:
        raise ValueError(
            f"Visual TypeTree metadata must be 40 bytes, got {len(typetree_metadata)}"
        )
    data.extend(typetree_metadata)

    # Write each element
    for elem in elements:
        data.extend(elem.to_bytes())

    return bytes(data)


def serialize_template_assets_array(
    elements: List[UXMLElementBinary], typetree_metadata: bytes
) -> bytes:
    """
    Serialize template assets array.

    Format:
      count (4 bytes)
      TypeTree metadata (12 bytes) - copied from original
      element data (variable)

    Args:
        elements: List of template asset elements to serialize
        typetree_metadata: 12-byte TypeTree metadata from original VTA

    Returns:
        Binary data for complete template assets array
    """
    data = bytearray()

    # Write count
    data.extend(struct.pack("<i", len(elements)))

    # Write TypeTree metadata (preserve original)
    if len(typetree_metadata) != 12:
        raise ValueError(
            f"Template TypeTree metadata must be 12 bytes, got {len(typetree_metadata)}"
        )
    data.extend(typetree_metadata)

    # Write each element
    for elem in elements:
        data.extend(elem.to_bytes())

    return bytes(data)
