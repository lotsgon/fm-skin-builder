"""
VTA Builder - Builds complete VTA binary from components

Combines:
- Fixed header (72 bytes)
- Template references section
- Visual elements array
- Template assets array
"""

from __future__ import annotations
from typing import List
from .vta_header_parser import parse_vta_header, serialize_template_references
from .vta_element_serializer import (
    serialize_visual_elements_array,
    serialize_template_assets_array,
)
from .uxml_element_parser import UXMLElementBinary


class VTABuilder:
    """Builds complete VTA binary from components."""

    def __init__(self, original_vta_binary: bytes):
        """
        Initialize with original VTA for metadata.

        Args:
            original_vta_binary: Original VTA binary data to extract metadata from
        """
        self.header = parse_vta_header(original_vta_binary)

    def build(
        self,
        visual_elements: List[UXMLElementBinary],
        template_elements: List[UXMLElementBinary],
    ) -> bytes:
        """
        Build complete VTA binary.

        Args:
            visual_elements: List of visual element objects
            template_elements: List of template asset element objects

        Returns:
            Complete VTA binary data
        """
        data = bytearray()

        # 1. Write fixed header (0-72)
        data.extend(self.header.fixed_header)

        # 2. Write template references section
        template_refs_data = serialize_template_references(self.header.template_refs)
        data.extend(template_refs_data)

        # 3. Write visual elements array
        visual_array = serialize_visual_elements_array(
            visual_elements, self.header.visual_typetree
        )
        data.extend(visual_array)

        # 4. Write template assets array
        template_array = serialize_template_assets_array(
            template_elements, self.header.template_typetree
        )
        data.extend(template_array)

        return bytes(data)
