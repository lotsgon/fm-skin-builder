"""
UXML Binary Patcher - Directly patch UXML assets by manipulating raw binary data.

This bypasses UnityPy's serialization issues by working directly with the binary format.
"""

import struct
from typing import Dict, Any, List, Optional
import logging

from .uxml_element_parser import (
    UXMLElementBinary,
    parse_element_at_offset,
    find_element_offset,
)

log = logging.getLogger(__name__)


class UXMLBinaryPatcher:
    """Patch UXML assets using direct binary manipulation."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def apply_uxml_to_vta_binary(
        self,
        raw_data: bytes,
        imported_data: Dict[str, Any],
        original_elements: List[Any]
    ) -> Optional[bytes]:
        """
        Apply UXML changes to VisualTreeAsset by directly patching binary data.

        This method bypasses UnityPy serialization completely.

        Args:
            raw_data: Raw binary data from obj.get_raw_data()
            imported_data: Parsed UXML data from UXMLImporter
            original_elements: Original element objects from UnityPy (for reference)

        Returns:
            Modified binary data or None if patching fails
        """
        try:
            # Parse all elements from binary
            elements = self._parse_all_elements(raw_data, original_elements)
            if not elements:
                log.error("Failed to parse elements from binary data")
                return None

            # Apply modifications from imported data
            self._apply_modifications(elements, imported_data['m_VisualElementAssets'])

            # Rebuild the asset with modified elements
            new_raw_data = self._rebuild_asset(raw_data, elements)

            if self.verbose:
                log.debug(f"Binary patch successful: {len(raw_data)} → {len(new_raw_data)} bytes")

            return new_raw_data

        except Exception as e:
            log.error(f"Failed to apply binary UXML patch: {e}")
            import traceback
            log.debug(traceback.format_exc())
            return None

    def _parse_all_elements(
        self,
        raw_data: bytes,
        original_elements: List[Any]
    ) -> Optional[List[UXMLElementBinary]]:
        """
        Parse all elements from raw binary data.

        Args:
            raw_data: Complete asset binary data
            original_elements: Original element objects from UnityPy

        Returns:
            List of parsed elements or None if parsing fails
        """
        elements = []

        for orig_elem in original_elements:
            offset = find_element_offset(raw_data, orig_elem.m_Id)
            if offset == -1:
                log.error(f"Could not find element {orig_elem.m_Id} in binary data")
                return None

            parsed = parse_element_at_offset(raw_data, offset, debug=self.verbose)
            if not parsed:
                log.error(f"Failed to parse element at offset {offset}")
                return None

            elements.append(parsed)

            if self.verbose:
                classes_str = ', '.join(f'"{c}"' for c in parsed.m_Classes) if parsed.m_Classes else 'none'
                log.debug(
                    f"Parsed element {parsed.m_Id}: order={parsed.m_OrderInDocument}, "
                    f"classes=[{classes_str}]"
                )

        return elements

    def _apply_modifications(
        self,
        elements: List[UXMLElementBinary],
        imported_elements: List[Dict[str, Any]]
    ):
        """
        Apply modifications from imported data to parsed elements.

        Matches elements by position (m_OrderInDocument) rather than ID,
        since UXML files don't preserve element IDs.

        Args:
            elements: Parsed binary elements (modified in-place)
            imported_elements: Imported element data from UXML
        """
        # Sort both lists by order to ensure correct matching
        elements_by_order = sorted(elements, key=lambda e: e.m_OrderInDocument)
        imported_by_order = sorted(imported_elements, key=lambda e: e['m_OrderInDocument'])

        # Handle count mismatch
        if len(elements_by_order) != len(imported_by_order):
            log.warning(
                f"Element count mismatch: original has {len(elements_by_order)} elements, "
                f"imported has {len(imported_by_order)} elements. "
                f"This may indicate added/removed elements which is not fully supported yet."
            )
            # For now, only process up to the minimum count
            min_count = min(len(elements_by_order), len(imported_by_order))
        else:
            min_count = len(elements_by_order)

        # Match and apply changes by position
        for i in range(min_count):
            elem = elements_by_order[i]
            imported = imported_by_order[i]

            # Preserve the original ID (don't change it)
            # Only update order if it changed
            if 'm_OrderInDocument' in imported and imported['m_OrderInDocument'] != elem.m_OrderInDocument:
                old_order = elem.m_OrderInDocument
                elem.m_OrderInDocument = imported['m_OrderInDocument']
                if self.verbose:
                    log.debug(
                        f"Element {elem.m_Id}: order {old_order} → {elem.m_OrderInDocument}"
                    )

            # Update parent ID mapping (map from imported position to original ID)
            # Note: Parent IDs need special handling since they reference other elements
            # For now, keep original parent relationships
            # TODO: Handle parent ID remapping for element hierarchy changes

            # Update CSS classes
            if 'm_Classes' in imported:
                old_classes = elem.m_Classes.copy()
                elem.m_Classes = imported['m_Classes']
                if self.verbose and old_classes != elem.m_Classes:
                    old_str = ', '.join(f'"{c}"' for c in old_classes) if old_classes else 'none'
                    new_str = ', '.join(f'"{c}"' for c in elem.m_Classes) if elem.m_Classes else 'none'
                    log.debug(
                        f"Element {elem.m_Id}: classes [{old_str}] → [{new_str}]"
                    )

    def _rebuild_asset(
        self,
        original_raw: bytes,
        elements: List[UXMLElementBinary]
    ) -> bytes:
        """
        Rebuild the asset binary data with modified elements.

        This is complex because:
        1. Elements are variable-length (due to string arrays)
        2. We need to preserve data before and after the elements array
        3. We need to update the elements array size field

        Args:
            original_raw: Original binary data
            elements: Modified elements

        Returns:
            New binary data with modified elements
        """
        if not elements:
            return original_raw

        # Find the start of the elements array
        # The array starts with an int32 count, then the elements
        first_elem_offset = elements[0].offset

        # The array size field is 4 bytes before the first element
        array_size_offset = first_elem_offset - 4

        # Find the last element's end
        last_elem = elements[-1]
        last_elem_end = last_elem.offset + len(last_elem)

        # Build new binary data
        result = bytearray()

        # 1. Keep everything before the elements array
        result.extend(original_raw[:array_size_offset])

        # 2. Write new array size (should be same)
        result.extend(struct.pack('<i', len(elements)))

        # 3. Write all elements
        for elem in elements:
            result.extend(elem.to_bytes())

        # 4. Keep everything after the elements array
        result.extend(original_raw[last_elem_end:])

        if self.verbose:
            log.debug(f"Rebuilt asset: {len(original_raw)} → {len(result)} bytes")

        return bytes(result)
