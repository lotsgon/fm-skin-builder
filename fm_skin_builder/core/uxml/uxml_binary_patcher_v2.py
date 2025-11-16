"""
UXML Binary Patcher V2 - Separate Array Handler

This version correctly handles m_VisualElementAssets and m_TemplateAssets
as separate arrays in the VTA binary structure.
"""

import struct
import logging
from typing import List, Dict, Any, Optional, Set
from fm_skin_builder.core.uxml.uxml_element_parser import (
    UXMLElementBinary,
    parse_element_at_offset,
    find_element_offset
)

log = logging.getLogger(__name__)


class UXMLBinaryPatcherV2:
    """Patches UXML elements using binary manipulation with separate array handling."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def apply_uxml_to_vta_binary(
        self,
        raw_data: bytes,
        imported_data: Dict[str, Any],
        visual_elements: List[Any],
        template_assets: List[Any]
    ) -> Optional[bytes]:
        """
        Apply UXML changes by directly patching binary data.

        Args:
            raw_data: Original binary data from VTA
            imported_data: Parsed UXML data with m_VisualElementAssets list
            visual_elements: Original m_VisualElementAssets from UnityPy
            template_assets: Original m_TemplateAssets from UnityPy

        Returns:
            Modified binary data or None if patching fails
        """
        if self.verbose:
            log.debug(f"Applying UXML patch to VTA binary ({len(raw_data)} bytes)")
            log.debug(f"  Original visual elements: {len(visual_elements)}")
            log.debug(f"  Original template assets: {len(template_assets)}")
            log.debug(f"  Imported UXML elements: {len(imported_data['m_VisualElementAssets'])}")

        # Parse visual elements from binary
        visual_parsed = self._parse_elements_from_array(raw_data, visual_elements)
        if visual_parsed is None:
            log.error("Failed to parse visual elements")
            return None

        # Parse template assets from binary
        template_parsed = self._parse_elements_from_array(raw_data, template_assets)
        if template_parsed is None:
            log.error("Failed to parse template assets")
            return None

        if self.verbose:
            log.debug(f"Parsed {len(visual_parsed)} visual elements and {len(template_parsed)} template assets from binary")

        # Apply modifications to both element lists
        self._apply_modifications(visual_parsed + template_parsed, imported_data['m_VisualElementAssets'])

        # Rebuild with separate arrays
        new_raw_data = self._rebuild_with_separate_arrays(
            raw_data, visual_parsed, template_parsed, visual_elements, template_assets
        )

        if new_raw_data:
            if self.verbose:
                log.debug(f"Binary patch successful: {len(raw_data)} → {len(new_raw_data)} bytes")
        else:
            log.error("Failed to rebuild asset with separate arrays")

        return new_raw_data

    def _parse_elements_from_array(
        self,
        raw_data: bytes,
        original_elements: List[Any]
    ) -> Optional[List[UXMLElementBinary]]:
        """Parse elements from a specific array (visual or template)."""
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
        all_elements: List[UXMLElementBinary],
        imported_elements: List[Dict[str, Any]]
    ) -> None:
        """Apply modifications from imported UXML to parsed elements."""
        # Build a lookup by element ID
        imported_by_id = {elem['m_Id']: elem for elem in imported_elements}
        matched_imported_ids: Set[int] = set()

        for elem in all_elements:
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
                    log.debug(
                        f"Element {elem.m_Id}: classes {old_classes} → {elem.m_Classes}"
                    )

            # Update stylesheet paths (rare)
            if 'm_StylesheetPaths' in imported:
                old_paths = elem.m_StylesheetPaths.copy()
                elem.m_StylesheetPaths = imported['m_StylesheetPaths']
                if self.verbose and old_paths != elem.m_StylesheetPaths:
                    log.debug(
                        f"Element {elem.m_Id}: paths {old_paths} → {elem.m_StylesheetPaths}"
                    )

        # Check for unmatched imports
        unmatched = set(imported_by_id.keys()) - matched_imported_ids
        if unmatched and self.verbose:
            log.warning(f"Found {len(unmatched)} elements in UXML that don't exist in original: {list(unmatched)}")

    def _rebuild_with_separate_arrays(
        self,
        original_raw: bytes,
        visual_elements: List[UXMLElementBinary],
        template_elements: List[UXMLElementBinary],
        orig_visual: List[Any],
        orig_template: List[Any]
    ) -> bytes:
        """
        Rebuild asset with separate m_VisualElementAssets and m_TemplateAssets arrays.

        VTA structure:
        - Header (offset 0-151)
        - m_VisualElementAssets count (offset 152)
        - m_VisualElementAssets type info (offset 156-191)
        - m_VisualElementAssets data (starts offset 192)
        - m_TemplateAssets count
        - m_TemplateAssets type info
        - m_TemplateAssets data
        - Footer
        """
        if not visual_elements and not template_elements:
            return original_raw

        result = bytearray()

        # Find visual elements array location
        if visual_elements:
            visual_array_offset = 152  # Known offset from analysis
            first_visual_elem_offset = visual_elements[0].offset

            # Calculate end of visual elements array
            last_visual = visual_elements[-1]
            visual_end = last_visual.offset + len(last_visual)
            # Add padding
            padding = (4 - (visual_end % 4)) % 4
            visual_end += padding

            if self.verbose:
                log.debug(f"Visual elements array:")
                log.debug(f"  Count field at: {visual_array_offset}")
                log.debug(f"  First element at: {first_visual_elem_offset}")
                log.debug(f"  Last element ends at: {visual_end}")

        # Find template assets array location
        if template_elements:
            first_template_elem_offset = template_elements[0].offset
            # Template array size field is 4 bytes before first template element
            template_array_offset = first_template_elem_offset - 4

            # Need to find type info section between arrays
            # Type info starts after visual array ends
            if visual_elements:
                type_info_start = visual_end
                type_info_end = template_array_offset
            else:
                # If no visual elements, find type info before templates
                type_info_start = 152  # Start of arrays section
                type_info_end = template_array_offset

            # Calculate end of template elements array
            last_template = template_elements[-1]
            template_end = last_template.offset + len(last_template)
            # Add padding
            padding = (4 - (template_end % 4)) % 4
            template_end += padding

            if self.verbose:
                log.debug(f"Template assets array:")
                log.debug(f"  Type info: {type_info_start}-{type_info_end}")
                log.debug(f"  Count field at: {template_array_offset}")
                log.debug(f"  First element at: {first_template_elem_offset}")
                log.debug(f"  Last element ends at: {template_end}")

        # Build new binary data

        # 1. Keep header (before visual elements array)
        result.extend(original_raw[:visual_array_offset])
        if self.verbose:
            log.debug(f"Kept header: {visual_array_offset} bytes")

        # 2. Write visual elements array
        if visual_elements:
            # Write count
            result.extend(struct.pack('<i', len(visual_elements)))

            # Write type info (copy from original)
            type_info = original_raw[visual_array_offset + 4:first_visual_elem_offset]
            result.extend(type_info)

            # Write elements with padding
            for i, elem in enumerate(visual_elements):
                elem_bytes = elem.to_bytes()
                result.extend(elem_bytes)

                # Add padding
                padding_needed = (4 - (len(result) % 4)) % 4
                if padding_needed > 0:
                    result.extend(bytes(padding_needed))

                if self.verbose:
                    log.debug(f"  Visual element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        # 3. Write template assets array
        if template_elements:
            # Copy type info between arrays
            result.extend(original_raw[visual_end:template_array_offset])

            # Write count
            result.extend(struct.pack('<i', len(template_elements)))

            # Write type info (copy from original)
            type_info = original_raw[template_array_offset + 4:first_template_elem_offset]
            result.extend(type_info)

            # Write elements with padding
            for i, elem in enumerate(template_elements):
                elem_bytes = elem.to_bytes()
                result.extend(elem_bytes)

                # Add padding
                padding_needed = (4 - (len(result) % 4)) % 4
                if padding_needed > 0:
                    result.extend(bytes(padding_needed))

                if self.verbose:
                    log.debug(f"  Template element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        # 4. Keep footer (after template elements array)
        footer_start = template_end if template_elements else visual_end
        result.extend(original_raw[footer_start:])
        if self.verbose:
            log.debug(f"Kept footer: {len(original_raw) - footer_start} bytes")
            log.debug(f"Rebuilt asset: {len(original_raw)} → {len(result)} bytes")

        return bytes(result)
