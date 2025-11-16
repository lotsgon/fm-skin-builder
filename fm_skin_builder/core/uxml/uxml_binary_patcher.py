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

        if self.verbose:
            log.debug(f"Parsing {len(original_elements)} elements from binary")

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
                paths_str = ', '.join(f'"{p}"' for p in parsed.m_StylesheetPaths) if parsed.m_StylesheetPaths else 'none'
                log.debug(
                    f"Parsed element {parsed.m_Id}: type={parsed.m_Type}, name={parsed.m_Name or '(empty)'}, "
                    f"order={parsed.m_OrderInDocument}, classes=[{classes_str}], paths=[{paths_str}]"
                )

        return elements

    def _apply_modifications(
        self,
        elements: List[UXMLElementBinary],
        imported_elements: List[Dict[str, Any]]
    ):
        """
        Apply modifications from imported data to parsed elements.

        Matches elements by ID. The UXML exporter preserves element IDs
        via data-unity-id attributes, enabling accurate matching.

        Args:
            elements: Parsed binary elements (modified in-place)
            imported_elements: Imported element data from UXML
        """
        # Create lookup by ID
        imported_by_id = {elem['m_Id']: elem for elem in imported_elements}

        # Track which imported elements were matched
        matched_imported_ids = set()

        for elem in elements:
            if elem.m_Id not in imported_by_id:
                if self.verbose:
                    log.debug(f"Element {elem.m_Id} not in imported data, keeping original")
                continue

            imported = imported_by_id[elem.m_Id]
            matched_imported_ids.add(elem.m_Id)

            # IMPORTANT: Do NOT update m_OrderInDocument or m_ParentId from UXML
            # These are internal VTA structure fields that should not be modified
            # The UXML importer generates these incorrectly, so we ignore them

            # Only update m_RuleIndex if explicitly provided (rare)
            # Most of the time this should not change
            # if 'm_RuleIndex' in imported:
            #     elem.m_RuleIndex = imported['m_RuleIndex']

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

        # Warn about any imported elements that weren't matched
        unmatched = set(imported_by_id.keys()) - matched_imported_ids
        if unmatched:
            log.warning(
                f"Found {len(unmatched)} elements in UXML that don't exist in original: {list(unmatched)[:5]}... "
                f"(adding new elements not yet supported)"
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

        # Calculate the last element's end using element parser
        # The last element also has padding after it for 4-byte alignment
        last_elem = elements[-1]

        # Calculate end based on actual element structure
        last_elem_end_without_padding = last_elem.offset + len(last_elem)

        # Account for padding to 4-byte boundary after last element
        # Unity aligns each element (including the last one) to 4-byte boundary
        last_elem_calculated_end = last_elem_end_without_padding
        padding_after_last = (4 - (last_elem_calculated_end % 4)) % 4
        last_elem_calculated_end += padding_after_last

        if self.verbose:
            log.debug(f"Rebuild info:")
            log.debug(f"  First element at offset {first_elem_offset}")
            log.debug(f"  Array size field at offset {array_size_offset}")
            log.debug(f"  Last element (ID {last_elem.m_Id}) at offset {last_elem.offset}")
            log.debug(f"  Last element calculated end: {last_elem_calculated_end}")
            log.debug(f"  Elements to write: {len(elements)}")

        # Build new binary data
        result = bytearray()

        # 1. Keep everything before the elements array
        result.extend(original_raw[:array_size_offset])
        if self.verbose:
            log.debug(f"  Kept {array_size_offset} bytes before array")

        # 2. Write new array size (should be same)
        result.extend(struct.pack('<i', len(elements)))

        # 3. Write all elements (with 4-byte alignment padding between them)
        total_elem_bytes = 0
        for i, elem in enumerate(elements):
            elem_bytes = elem.to_bytes()
            result.extend(elem_bytes)
            total_elem_bytes += len(elem_bytes)

            # Add padding to align to 4-byte boundary
            # Unity pads each element to 4-byte alignment
            padding_needed = (4 - (len(result) % 4)) % 4
            if padding_needed > 0:
                result.extend(bytes(padding_needed))
                total_elem_bytes += padding_needed

            if self.verbose:
                log.debug(f"  Element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        if self.verbose:
            log.debug(f"  Total element bytes written: {total_elem_bytes}")

        # 4. Keep everything after the elements array
        bytes_after = len(original_raw) - last_elem_calculated_end
        result.extend(original_raw[last_elem_calculated_end:])
        if self.verbose:
            log.debug(f"  Kept {bytes_after} bytes after array")
            log.debug(f"Rebuilt asset: {len(original_raw)} → {len(result)} bytes")

        return bytes(result)
