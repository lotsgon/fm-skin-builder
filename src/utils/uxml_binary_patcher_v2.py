"""
Enhanced UXML Binary Patcher with full element support including CSS classes.

This version properly handles variable-length elements and can modify:
- Integer fields (m_Id, m_OrderInDocument, m_ParentId, m_RuleIndex)
- String arrays (m_Classes)
"""

import struct
from pathlib import Path
from typing import Dict, Any, List, Optional
import UnityPy
from .uxml_element_parser import (
    UXMLElementBinary,
    parse_element_at_offset,
    find_element_offset,
    rebuild_element_section
)


class UXMLBinaryPatcherV2:
    """Enhanced UXML patcher with full element support."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def patch_uxml_asset(
        self,
        bundle_path: Path,
        asset_name: str,
        imported_data: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """
        Patch a UXML asset with full support for CSS classes and other fields.

        Args:
            bundle_path: Path to source bundle
            asset_name: Name of UXML asset
            imported_data: Parsed UXML data from UXMLImporter
            output_path: Where to save modified bundle

        Returns:
            True if successful
        """
        try:
            env = UnityPy.load(str(bundle_path))

            for obj in env.objects:
                if obj.type.name != "MonoBehaviour":
                    continue

                try:
                    data = obj.read()

                    if not hasattr(data, 'm_Name') or data.m_Name != asset_name:
                        continue

                    if not hasattr(data, 'm_VisualElementAssets'):
                        continue

                    if self.verbose:
                        print(f"Found asset: {asset_name}")
                        print(
                            f"  Original elements: {len(data.m_VisualElementAssets)}")
                        print(
                            f"  Imported elements: {len(imported_data['m_VisualElementAssets'])}")

                    # Get raw binary data
                    raw_data = obj.get_raw_data()

                    # Parse all elements
                    elements = self._parse_all_elements(
                        raw_data, data.m_VisualElementAssets)
                    if not elements:
                        print("✗ Failed to parse elements")
                        return False

                    # Apply modifications from imported data
                    self._apply_modifications(
                        elements, imported_data['m_VisualElementAssets'])

                    # Rebuild the asset with modified elements
                    new_raw_data = self._rebuild_asset(raw_data, elements)

                    # Set modified data
                    obj.set_raw_data(new_raw_data)

                    # Save bundle
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(env.file.save())

                    if self.verbose:
                        print(f"✓ Saved to: {output_path}")

                    return True

                except Exception as e:
                    if self.verbose:
                        print(f"Error processing object: {e}")
                        import traceback
                        traceback.print_exc()
                    continue

            print(f"✗ Asset '{asset_name}' not found in bundle")
            return False

        except Exception as e:
            print(f"✗ Error patching bundle: {e}")
            import traceback
            traceback.print_exc()
            return False

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
                print(f"✗ Could not find element {orig_elem.m_Id}")
                return None

            parsed = parse_element_at_offset(raw_data, offset)
            if not parsed:
                print(f"✗ Failed to parse element at offset {offset}")
                return None

            elements.append(parsed)

            if self.verbose:
                classes_str = ', '.join(
                    f'"{c}"' for c in parsed.m_Classes) if parsed.m_Classes else 'none'
                print(
                    f"  Parsed element {parsed.m_Id}: order={parsed.m_OrderInDocument}, classes=[{classes_str}]")

        return elements

    def _apply_modifications(
        self,
        elements: List[UXMLElementBinary],
        imported_elements: List[Dict[str, Any]]
    ):
        """
        Apply modifications from imported data to parsed elements.

        Args:
            elements: Parsed binary elements (modified in-place)
            imported_elements: Imported element data from XML
        """
        # Create lookup by ID
        imported_by_id = {elem['m_Id']: elem for elem in imported_elements}

        for elem in elements:
            if elem.m_Id not in imported_by_id:
                continue

            imported = imported_by_id[elem.m_Id]

            # Update integer fields
            if 'm_OrderInDocument' in imported:
                old_order = elem.m_OrderInDocument
                elem.m_OrderInDocument = imported['m_OrderInDocument']
                if self.verbose and old_order != elem.m_OrderInDocument:
                    print(
                        f"    Element {elem.m_Id}: order {old_order} → {elem.m_OrderInDocument}")

            if 'm_ParentId' in imported:
                old_parent = elem.m_ParentId
                elem.m_ParentId = imported['m_ParentId']
                if self.verbose and old_parent != elem.m_ParentId:
                    print(
                        f"    Element {elem.m_Id}: parent {old_parent} → {elem.m_ParentId}")

            if 'm_RuleIndex' in imported:
                elem.m_RuleIndex = imported['m_RuleIndex']

            # Update CSS classes
            if 'm_Classes' in imported:
                old_classes = elem.m_Classes.copy()
                elem.m_Classes = imported['m_Classes']
                if self.verbose and old_classes != elem.m_Classes:
                    old_str = ', '.join(
                        f'"{c}"' for c in old_classes) if old_classes else 'none'
                    new_str = ', '.join(
                        f'"{c}"' for c in elem.m_Classes) if elem.m_Classes else 'none'
                    print(
                        f"    Element {elem.m_Id}: classes [{old_str}] → [{new_str}]")

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
        # Find the start of the elements array
        # The array starts with an int32 count, then the elements
        # We need to find where this array starts in the binary data

        if not elements:
            return original_raw

        # Find the first element's offset
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
            print(
                f"  Rebuilt asset: {len(original_raw)} → {len(result)} bytes")

        return bytes(result)


def patch_uxml_from_xml(
    bundle_path: Path,
    asset_name: str,
    xml_path: Path,
    output_path: Path,
    verbose: bool = False
) -> bool:
    """
    Convenience function to patch UXML from an XML file.

    Args:
        bundle_path: Path to source bundle
        asset_name: Name of UXML asset
        xml_path: Path to XML file with modifications
        output_path: Where to save modified bundle
        verbose: Enable verbose output

    Returns:
        True if successful
    """
    from .uxml_importer import UXMLImporter

    # Parse XML file
    importer = UXMLImporter()
    imported_data = importer.parse_uxml_file(str(xml_path))

    if not imported_data:
        print(f"✗ Failed to import {xml_path}")
        return False

    # Apply patches
    patcher = UXMLBinaryPatcherV2(verbose=verbose)
    return patcher.patch_uxml_asset(bundle_path, asset_name, imported_data, output_path)
