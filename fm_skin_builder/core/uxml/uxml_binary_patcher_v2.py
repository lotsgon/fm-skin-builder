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
        # Combine both visual and template arrays from imported data
        imported_all = imported_data['m_VisualElementAssets'] + imported_data.get('m_TemplateAssets', [])
        self._apply_modifications(visual_parsed + template_parsed, imported_all)

        # Try in-place patching (preserves exact binary structure Unity expects)
        raw_modified = bytearray(raw_data)
        success = self._patch_elements_in_place(
            raw_modified, visual_parsed + template_parsed
        )

        if success:
            if self.verbose:
                log.debug(f"Binary patch successful: {len(raw_data)} bytes (in-place)")
            return bytes(raw_modified)
        else:
            # In-place patching failed (likely due to element growth)
            # Rebuild method produces bundles that crash the game, so return None
            log.error("In-place patching failed due to element growth - cannot patch this UXML")
            log.error("To fix: reduce the size of modified elements (shorter class names, etc.)")
            return None

    def _parse_elements_from_array(
        self,
        raw_data: bytes,
        original_elements: List[Any]
    ) -> Optional[List[UXMLElementBinary]]:
        """Parse elements from a specific array (visual or template).

        Uses UnityPy's already-parsed element data instead of custom binary parsing.
        """
        elements = []

        if self.verbose:
            log.debug(f"Converting {len(original_elements)} elements from UnityPy format")

        if not original_elements:
            if self.verbose:
                log.debug("No elements in array, skipping")
            return elements

        # Calculate original sizes by finding next element offset
        offsets_and_elems = []
        for i, orig_elem in enumerate(original_elements):
            offset = find_element_offset(raw_data, orig_elem.m_Id)
            if offset == -1:
                log.warning(f"Could not find element {orig_elem.m_Id} in binary data")
                offset = 0
            offsets_and_elems.append((offset, orig_elem, i))

        # Sort by offset to calculate sizes
        offsets_and_elems.sort(key=lambda x: x[0])

        for idx, (offset, orig_elem, i) in enumerate(offsets_and_elems):
            if offset == 0:
                log.warning(f"Skipping element {orig_elem.m_Id} with offset 0")
                continue

            # Use parse_element_at_offset to get the complete binary structure
            element = parse_element_at_offset(raw_data, offset, debug=False)

            if element is None:
                log.warning(f"Failed to parse element at offset {offset}, skipping")
                continue

            # Verify the element ID matches
            if element.m_Id != orig_elem.m_Id:
                log.warning(f"Element ID mismatch at offset {offset}: expected {orig_elem.m_Id}, got {element.m_Id}")
                # Still use it - the offset might be slightly wrong but the parse succeeded

            # Store the parsed element
            try:
                elements.append(element)

                if self.verbose:
                    classes_str = ', '.join(f'"{c}"' for c in element.m_Classes) if element.m_Classes else 'none'
                    paths_str = ', '.join(f'"{p}"' for p in element.m_StylesheetPaths) if element.m_StylesheetPaths else 'none'
                    log.debug(
                        f"Converted element {element.m_Id}: type={element.m_Type}, name={element.m_Name or '(empty)'}, "
                        f"order={element.m_OrderInDocument}, classes=[{classes_str}], paths=[{paths_str}]"
                    )

            except Exception as e:
                log.error(f"Failed to convert UnityPy element {i}: {e}")
                return None

        return elements

    def _patch_elements_in_place(
        self,
        raw_data: bytearray,
        elements: List[UXMLElementBinary]
    ) -> bool:
        """
        Patch elements in-place by modifying only the m_Classes array.

        This preserves the exact binary structure for all other fields.

        Args:
            raw_data: Mutable binary data to patch
            elements: List of modified elements

        Returns:
            True if successful
        """
        import struct

        for elem in elements:
            if elem.offset == 0:
                log.warning(f"Element {elem.m_Id} has offset 0, skipping")
                continue

            # Calculate where m_Classes array starts (after 36 bytes of fixed fields)
            classes_offset = elem.offset + 36

            # Read current classes array to calculate its size
            if classes_offset + 4 > len(raw_data):
                log.error(f"Element {elem.m_Id}: offset out of bounds")
                return False

            old_count = struct.unpack_from('<i', raw_data, classes_offset)[0]

            # Calculate old classes array size
            old_size = 4  # count field
            pos = classes_offset + 4
            for i in range(old_count):
                if pos + 4 > len(raw_data):
                    log.error(f"Element {elem.m_Id}: not enough data to read class string {i}")
                    return False
                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                if str_len < 0 or str_len > 1000:
                    print(f"[PATCH DEBUG] Element {elem.m_Id}: unreasonable class string length: {str_len} at class {i}/{old_count}")
                    print(f"[PATCH DEBUG]   Position in raw_data: {pos}, classes_offset: {classes_offset}")
                    print(f"[PATCH DEBUG]   Hex at position: {raw_data[pos:pos+16].hex()}")
                    return False
                pos += 4 + str_len  # length + data (NO null terminator)
                # Strings are packed together without nulls

            # Add alignment padding for entire array
            remainder = pos % 4
            if remainder != 0:
                pos += 4 - remainder

            old_size = pos - classes_offset

            # Serialize new classes array
            new_classes_bytes = bytearray()
            new_classes_bytes.extend(struct.pack('<i', len(elem.m_Classes)))
            for class_name in elem.m_Classes:
                class_bytes = class_name.encode('utf-8')
                new_classes_bytes.extend(struct.pack('<i', len(class_bytes)))
                new_classes_bytes.extend(class_bytes)
                # NO null terminator - strings are packed together

            # Add alignment padding for entire array
            while len(new_classes_bytes) % 4 != 0:
                new_classes_bytes.append(0)

            # Check if new array fits
            if len(new_classes_bytes) > old_size:
                print(f"[PATCH DEBUG] Element {elem.m_Id}: classes array grew from {old_size} to {len(new_classes_bytes)} bytes")
                print(f"[PATCH DEBUG]   Old classes (count={old_count})")
                print(f"[PATCH DEBUG]   New classes (count={len(elem.m_Classes)}): {elem.m_Classes}")
                return False

            # Patch the classes array in-place
            raw_data[classes_offset:classes_offset + len(new_classes_bytes)] = new_classes_bytes

            # If smaller, we might need to shift data or just leave it
            # For now, just leave the extra bytes (they'll be ignored by Unity)

            if self.verbose:
                log.debug(f"Patched element {elem.m_Id} classes array: {old_count} → {len(elem.m_Classes)} items")

        return True

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
        # NOTE: Offset 12 is NOT used - it's just part of the header!
        # TypeTree reads array counts INLINE at the start of each array.
        VISUAL_COUNT_OFFSET = 152  # Visual array starts here (inline count)
        TYPE_INFO_START = 156       # Type info for visual elements
        FIRST_VISUAL_OFFSET = 196   # First visual element data

        # Calculate visual elements end (in ORIGINAL binary)
        if visual_elements:
            last_visual = visual_elements[-1]
            # Use original_size to find where it ended in the original binary
            visual_data_end = last_visual.offset + last_visual.original_size
            # Add padding
            padding = (4 - (visual_data_end % 4)) % 4
            visual_data_end += padding

            if self.verbose:
                log.debug("Visual elements:")
                log.debug(f"  Count: {len(visual_elements)}")
                log.debug(f"  Data ends at: {visual_data_end} (in original binary)")
        else:
            visual_data_end = FIRST_VISUAL_OFFSET

        # Calculate template elements end (in ORIGINAL binary)
        if template_elements:
            # Templates start right after visual elements
            first_template_offset = template_elements[0].offset
            last_template = template_elements[-1]
            # Use original_size to find where it ended in the original binary
            template_data_end = last_template.offset + last_template.original_size
            # Add padding
            padding = (4 - (template_data_end % 4)) % 4
            template_data_end += padding

            if self.verbose:
                log.debug("Template assets:")
                log.debug(f"  Count: {len(template_elements)}")
                log.debug(f"  First at: {first_template_offset}")
                log.debug(f"  Data ends at: {template_data_end} (in original binary)")
        else:
            template_data_end = visual_data_end

        # Build new binary data
        # CRITICAL: TypeTree reads array counts INLINE at the start of each array,
        # NOT from header offsets! Offset 152 is the visual array start (with inline count).
        # Template array count is INLINE where the template array starts.

        # 1. Keep entire header (0-151) - DO NOT modify offset 12!
        result.extend(original_raw[:VISUAL_COUNT_OFFSET])

        # 2. Write visual count INLINE at offset 152 (this is correct!)
        result.extend(struct.pack('<i', len(visual_elements)))
        if self.verbose:
            log.debug(f"Updated visual count at offset {VISUAL_COUNT_OFFSET}: {len(visual_elements)}")

        # 3. Keep type info (156-195)
        result.extend(original_raw[TYPE_INFO_START:FIRST_VISUAL_OFFSET])
        if self.verbose:
            log.debug(f"Kept type info: {FIRST_VISUAL_OFFSET - TYPE_INFO_START} bytes")

        # 4. Write visual elements
        for i, elem in enumerate(visual_elements):
            elem_bytes = elem.to_bytes()
            result.extend(elem_bytes)

            # Add padding
            padding_needed = (4 - (len(result) % 4)) % 4
            if padding_needed > 0:
                result.extend(bytes(padding_needed))

            if self.verbose:
                log.debug(f"  Visual element {i} (ID {elem.m_Id}): {len(elem_bytes)} bytes + {padding_needed} padding")

        # 5. Write template count INLINE (TypeTree reads it from here!)
        result.extend(struct.pack('<i', len(template_elements)))
        if self.verbose:
            log.debug(f"  Template count (inline at offset {len(result)-4}): {len(template_elements)}")

        # 6. Write template elements
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
