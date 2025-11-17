"""
VTA Patcher - Patch individual elements in-place within raw VTA arrays

This enables modifications while preserving Unity metadata, padding, and structure.
"""

from __future__ import annotations
from .vta_header_parser import parse_vta_header
from .uxml_element_parser import UXMLElementBinary, find_element_offset


class VTAPatcher:
    """Patches individual elements in a VTA while preserving structure."""

    def __init__(self, original_vta_binary: bytes):
        """
        Initialize with original VTA.

        Args:
            original_vta_binary: Original VTA binary data
        """
        self.original = original_vta_binary
        self.header = parse_vta_header(original_vta_binary)
        self.modifications = {}  # element_id -> modified UXMLElementBinary

    def patch_element(self, element: UXMLElementBinary) -> None:
        """
        Mark an element for patching.

        Args:
            element: Modified element to patch into VTA
        """
        self.modifications[element.m_Id] = element

    def build(self) -> bytes:
        """
        Build VTA with patched elements.

        Returns:
            Complete VTA binary with patches applied
        """
        # Start with copy of original
        data = bytearray(self.original)

        # Apply each modification
        for element_id, modified_element in self.modifications.items():
            # Find element in original
            offset = find_element_offset(self.original, element_id)
            if offset == -1:
                raise ValueError(f"Cannot find element {element_id} to patch")

            # Serialize modified element
            modified_bytes = modified_element.to_bytes()

            # Check if size matches original
            if modified_element.original_size != len(modified_bytes):
                # Size changed - this is complex, would need to rebuild entire array
                raise ValueError(
                    f"Element {element_id} size changed: "
                    f"original={modified_element.original_size}, "
                    f"modified={len(modified_bytes)}. "
                    f"In-place patching only supports same-size modifications. "
                    f"Use VTABuilder with use_raw_arrays=False for structural changes."
                )

            # Patch in-place
            data[offset : offset + len(modified_bytes)] = modified_bytes

        return bytes(data)
