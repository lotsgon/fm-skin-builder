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

        CORRECT VTA structure:
        - offset 0-11:      Header part 1
        - offset 12:        Template assets count (int32)
        - offset 16-151:    Header part 2
        - offset 152:       Visual elements count (int32)
        - offset 156-195:   Visual elements type info (40 bytes)
        - offset 196+:      Visual elements data
        - after visual:     Template assets data (uses count from offset 12)
        - footer:           Remaining data
        """
        if not visual_elements and not template_elements:
            return original_raw

        result = bytearray()

        # Constants from analysis
        TEMPLATE_COUNT_OFFSET = 12
        VISUAL_COUNT_OFFSET = 152
        TYPE_INFO_START = 156
        FIRST_VISUAL_OFFSET = 196

        # Calculate visual elements end
        if visual_elements:
            last_visual = visual_elements[-1]
            visual_data_end = last_visual.offset + len(last_visual)
            # Add padding
            padding = (4 - (visual_data_end % 4)) % 4
            visual_data_end += padding

            if self.verbose:
                log.debug(f"Visual elements:")
                log.debug(f"  Count: {len(visual_elements)}")
                log.debug(f"  Data ends at: {visual_data_end}")
        else:
            visual_data_end = FIRST_VISUAL_OFFSET

        # Calculate template elements end
        if template_elements:
            # Templates start right after visual elements
            first_template_offset = template_elements[0].offset
            last_template = template_elements[-1]
            template_data_end = last_template.offset + len(last_template)
            # Add padding
            padding = (4 - (template_data_end % 4)) % 4
            template_data_end += padding

            if self.verbose:
                log.debug(f"Template assets:")
                log.debug(f"  Count: {len(template_elements)}")
                log.debug(f"  First at: {first_template_offset}")
                log.debug(f"  Data ends at: {template_data_end}")
        else:
            template_data_end = visual_data_end

        # Build new binary data

        # 1. Keep header part 1 (0-11)
        result.extend(original_raw[:TEMPLATE_COUNT_OFFSET])

        # 2. Write template count (offset 12)
        result.extend(struct.pack('<i', len(template_elements)))
        if self.verbose:
            log.debug(f"Updated template count at offset {TEMPLATE_COUNT_OFFSET}: {len(template_elements)}")

        # 3. Keep header part 2 (16-151)
        result.extend(original_raw[16:VISUAL_COUNT_OFFSET])

        # 4. Write visual count (offset 152)
        result.extend(struct.pack('<i', len(visual_elements)))
        if self.verbose:
            log.debug(f"Updated visual count at offset {VISUAL_COUNT_OFFSET}: {len(visual_elements)}")

        # 5. Keep type info (156-195)
        result.extend(original_raw[TYPE_INFO_START:FIRST_VISUAL_OFFSET])
        if self.verbose:
            log.debug(f"Kept type info: {FIRST_VISUAL_OFFSET - TYPE_INFO_START} bytes")

        # 6. Write visual elements
        for i, elem in enumerate(visual_elements):
            elem_bytes = elem.to_bytes()
            result.extend(elem_bytes)

            # Add padding
            padding_needed = (4 - (len(result) % 4)) % 4
            if padding_needed > 0:
                result.extend(bytes(padding_needed))

            if self.verbose:
                log.debug(f"  Visual element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        # 7. Write template elements (directly after visual, no gap)
        for i, elem in enumerate(template_elements):
            elem_bytes = elem.to_bytes()
            result.extend(elem_bytes)

            # Add padding
            padding_needed = (4 - (len(result) % 4)) % 4
            if padding_needed > 0:
                result.extend(bytes(padding_needed))

            if self.verbose:
                log.debug(f"  Template element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        # 8. Keep footer (everything after template elements)
        result.extend(original_raw[template_data_end:])
        if self.verbose:
            log.debug(f"Kept footer: {len(original_raw) - template_data_end} bytes")
            log.debug(f"Rebuilt asset: {len(original_raw)} → {len(result)} bytes")

        return bytes(result)
