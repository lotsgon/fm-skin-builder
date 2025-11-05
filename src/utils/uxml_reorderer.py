"""
UXML Element Reorderer - Reorder elements based on XML hierarchy.

This module provides a safer way to modify UXML element order:
1. Parse XML to get desired element order (based on hierarchy)
2. Find each element in binary data
3. Update ONLY m_OrderInDocument to match XML position
4. Keep all other fields unchanged (IDs, parents, CSS, etc.)

This avoids corruption by not trying to rebuild complex structures.
"""

import struct
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path


class UXMLReorderer:
    """Reorder UXML elements based on XML hierarchy."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def reorder_from_xml(
        self,
        raw_data: bytearray,
        xml_path: Path,
        original_elements: List[Any]
    ) -> bool:
        """
        Reorder elements based on XML hierarchy.

        Args:
            raw_data: Raw binary data to modify
            xml_path: Path to XML file with desired hierarchy
            original_elements: Original UnityPy element objects

        Returns:
            True if successful
        """
        # Parse XML to get element order
        element_order = self._parse_xml_order(xml_path)

        if not element_order:
            print("  ✗ Failed to parse XML element order")
            return False

        # Create ID to order mapping
        id_to_order = {elem_id: order for order,
                       elem_id in enumerate(element_order)}

        if self.verbose:
            print(f"  Parsed {len(element_order)} elements from XML")

        # Update m_OrderInDocument for each element
        patched_count = 0

        for orig_elem in original_elements:
            elem_id = orig_elem.m_Id

            # Skip elements not in XML (shouldn't happen)
            if elem_id not in id_to_order:
                if self.verbose:
                    print(
                        f"  Warning: Element {elem_id} not in XML, keeping original order")
                continue

            # Find element in binary
            offset = self._find_element_offset(raw_data, elem_id)

            if offset is None:
                print(f"  ✗ Could not locate element {elem_id} in raw data")
                return False

            # Update ONLY m_OrderInDocument (at offset+4)
            new_order = id_to_order[elem_id]
            struct.pack_into('<i', raw_data, offset + 4, new_order)

            if self.verbose and elem_id in [1752032402, -753365010]:
                print(
                    f"  Reordered element {elem_id}: {orig_elem.m_OrderInDocument} -> {new_order}")

            patched_count += 1

        if self.verbose:
            print(f"  ✓ Reordered {patched_count} elements")

        return True

    def _parse_xml_order(self, xml_path: Path) -> List[int]:
        """
        Parse XML file to get element IDs in document order.

        Args:
            xml_path: Path to XML file

        Returns:
            List of element IDs in document order
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Remove namespace for easier processing
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}')[1]

            element_ids = []

            def process_element(elem: ET.Element):
                """Recursively collect element IDs in document order."""
                # Get element ID from data-unity-id attribute
                unity_id_str = elem.get('data-unity-id')
                if unity_id_str:
                    try:
                        element_id = int(unity_id_str)
                        element_ids.append(element_id)
                    except ValueError:
                        pass

                # Process children (skip Template includes)
                for child in elem:
                    if child.tag != 'Template':
                        process_element(child)

            # Process all top-level elements
            for child in root:
                process_element(child)

            return element_ids

        except Exception as e:
            print(f"  ✗ Error parsing XML: {e}")
            return []

    def _find_element_offset(
        self,
        raw_data: bytearray,
        element_id: int
    ) -> Optional[int]:
        """
        Find the byte offset of an element by its ID.

        Args:
            raw_data: Raw binary data
            element_id: Element m_Id to find

        Returns:
            Byte offset or None if not found
        """
        # Search for element ID
        id_bytes = struct.pack('<i', element_id)
        offset = raw_data.find(id_bytes)

        if offset == -1:
            return None

        return offset
