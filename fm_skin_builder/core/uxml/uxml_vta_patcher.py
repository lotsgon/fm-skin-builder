"""
UXML VTA Patcher - Apply UXML edits to VTA binary

Bridges the gap between UXML export/import and VTA binary patching.
Enables workflow: Export VTA → Edit UXML → Patch VTA with changes.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Any
from .vta_patcher import VTAPatcher
from .uxml_element_parser import (
    UXMLElementBinary,
)
from .uxml_importer import UXMLImporter
from ..logger import get_logger

log = get_logger(__name__)


class UXMLVTAPatcher:
    """Applies UXML changes to VTA binaries."""

    def __init__(self, original_vta: bytes):
        """
        Initialize with original VTA binary.

        Args:
            original_vta: Original VTA binary data
        """
        self.original_vta = original_vta
        self.patcher = VTAPatcher(original_vta)
        self.changes: List[str] = []

    def apply_uxml_changes(self, uxml_path: Path) -> bytes:
        """
        Apply changes from edited UXML file to VTA.

        Workflow:
        1. Parse original VTA to get all elements with full binary data
        2. Parse edited UXML to get user's changes
        3. Match elements by data-unity-id
        4. Apply changes to binary elements
        5. Patch VTA with modified elements

        Args:
            uxml_path: Path to edited UXML file

        Returns:
            Modified VTA binary

        Raises:
            ValueError: If changes would alter element sizes
        """
        log.info(f"Applying UXML changes from {uxml_path}")

        # Step 1: Parse UXML to get changes
        importer = UXMLImporter()
        uxml_dict = importer.parse_uxml_to_dict(uxml_path)

        visual_changes = uxml_dict.get("m_VisualElementAssets", [])
        template_changes = uxml_dict.get("m_TemplateAssets", [])

        log.info(
            f"Found {len(visual_changes)} visual + {len(template_changes)} template elements in UXML"
        )

        # Step 2: Parse original VTA to get binary elements
        # We need to match by m_Id from UXML's data-unity-id
        original_elements = self._parse_original_elements()

        log.info(f"Parsed {len(original_elements)} elements from original VTA")

        # Step 3: Apply changes to matched elements
        modified_count = 0

        for change_dict in visual_changes + template_changes:
            elem_id = change_dict.get("m_Id")
            if elem_id is None:
                continue

            # Find matching element in original
            if elem_id not in original_elements:
                log.warning(f"Element {elem_id} from UXML not found in original VTA")
                continue

            original_elem = original_elements[elem_id]

            # Apply changes
            if self._apply_element_changes(original_elem, change_dict):
                self.patcher.patch_element(original_elem)
                modified_count += 1

        log.info(f"Applied changes to {modified_count} elements")

        # Step 4: Build patched VTA
        return self.patcher.build()

    def _parse_original_elements(self) -> Dict[int, UXMLElementBinary]:
        """
        Parse all elements from original VTA.

        Returns:
            Dictionary mapping element ID to UXMLElementBinary
        """
        # We need UnityPy to get the element list
        # For now, scan through the VTA binary looking for elements
        # This is a simplified version - in production we'd use UnityPy

        # TODO: Use UnityPy to get m_VisualElementAssets list
        # Then parse each element using find_element_offset + parse_element_at_offset

        # For now, return empty dict (will be filled by UnityPy integration)
        return {}

    def _apply_element_changes(
        self, element: UXMLElementBinary, changes: Dict[str, Any]
    ) -> bool:
        """
        Apply changes from UXML dict to UXMLElementBinary.

        Only applies same-size changes to enable in-place patching.

        Args:
            element: Original element to modify
            changes: Dictionary of changes from UXML

        Returns:
            True if changes were applied, False otherwise

        Raises:
            ValueError: If changes would alter element size
        """
        modified = False
        original_size = element.original_size

        # Apply m_Name changes
        new_name = changes.get("m_Name")
        if new_name is not None and new_name != element.m_Name:
            # Check size impact
            old_name_size = len(element.m_Name.encode("utf-8"))
            new_name_size = len(new_name.encode("utf-8"))

            if old_name_size != new_name_size:
                raise ValueError(
                    f"Name change would alter element size: "
                    f"'{element.m_Name}' ({old_name_size} bytes) → "
                    f"'{new_name}' ({new_name_size} bytes). "
                    f"In-place patching requires same-size modifications."
                )

            element.m_Name = new_name
            modified = True
            self.changes.append(f"Element {element.m_Id}: m_Name → '{new_name}'")

        # Apply m_Classes changes (CSS classes)
        new_classes = changes.get("m_Classes")
        if new_classes is not None:
            # Check size impact
            old_classes_size = sum(len(c.encode("utf-8")) for c in element.m_Classes)
            new_classes_size = sum(len(c.encode("utf-8")) for c in new_classes)

            if old_classes_size != new_classes_size:
                raise ValueError(
                    f"Classes change would alter element size: "
                    f"{element.m_Classes} ({old_classes_size} bytes) → "
                    f"{new_classes} ({new_classes_size} bytes). "
                    f"In-place patching requires same-size modifications."
                )

            element.m_Classes = new_classes
            modified = True
            self.changes.append(
                f"Element {element.m_Id}: m_Classes → {new_classes}"
            )

        # Verify total size hasn't changed
        if modified:
            new_size = len(element.to_bytes())
            if new_size != original_size:
                raise ValueError(
                    f"Element {element.m_Id} size changed: {original_size} → {new_size}. "
                    f"This should not happen for same-size string modifications."
                )

        return modified


def patch_vta_from_uxml(
    original_vta: bytes, uxml_path: Path
) -> tuple[bytes, List[str]]:
    """
    Convenience function to patch VTA from edited UXML.

    Args:
        original_vta: Original VTA binary
        uxml_path: Path to edited UXML file

    Returns:
        Tuple of (modified VTA binary, list of changes applied)
    """
    patcher = UXMLVTAPatcher(original_vta)
    modified_vta = patcher.apply_uxml_changes(uxml_path)
    return modified_vta, patcher.changes
