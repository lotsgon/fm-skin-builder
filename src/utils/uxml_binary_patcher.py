"""
UXML Binary Patcher - Directly modify UXML assets in Unity bundles.

This module bypasses UnityPy's broken save_typetree() by manipulating raw binary data.
"""

import struct
from pathlib import Path
from typing import Dict, Any, List, Optional
import UnityPy


class UXMLBinaryPatcher:
    """Patches UXML assets by directly modifying binary data."""

    def __init__(self):
        self.verbose = False

    def patch_uxml_asset(
        self,
        bundle_path: Path,
        asset_name: str,
        imported_data: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """
        Patch a UXML asset in a bundle with imported data.

        Args:
            bundle_path: Path to source bundle
            asset_name: Name of UXML asset to patch (e.g., "PlayerAttributesTile")
            imported_data: Parsed UXML data from UXMLImporter
            output_path: Where to save modified bundle

        Returns:
            True if successful, False otherwise
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
                    raw_mod = bytearray(raw_data)

                    # Patch elements
                    success = self._patch_elements(
                        raw_mod,
                        data.m_VisualElementAssets,
                        imported_data['m_VisualElementAssets']
                    )

                    if not success:
                        return False

                    # Set modified data back
                    obj.set_raw_data(bytes(raw_mod))

                    # Save bundle
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(env.file.save())

                    if self.verbose:
                        print(f"✓ Saved to: {output_path}")

                    return True

                except Exception as e:
                    if self.verbose:
                        print(f"Error reading object: {e}")
                    continue

            print(f"✗ Asset '{asset_name}' not found in bundle")
            return False

        except Exception as e:
            print(f"✗ Error patching bundle: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _patch_elements(
        self,
        raw_data: bytearray,
        original_elements: List[Any],
        imported_elements: List[Dict[str, Any]]
    ) -> bool:
        """
        Patch visual element data in raw binary.

        Args:
            raw_data: Raw binary data to modify
            original_elements: Original UnityPy element objects
            imported_elements: Imported element dicts with new values

        Returns:
            True if successful
        """
        # Create ID to imported element mapping
        id_map = {elem['m_Id']: elem for elem in imported_elements}

        patched_count = 0

        for orig_elem in original_elements:
            elem_id = orig_elem.m_Id

            # Find this element in imported data
            if elem_id not in id_map:
                if self.verbose:
                    print(
                        f"  Warning: Element {elem_id} not in imported data, skipping")
                continue

            imported_elem = id_map[elem_id]

            # Find element in raw data
            offset = self._find_element_offset(raw_data, orig_elem)

            if offset is None:
                print(f"  ✗ Could not locate element {elem_id} in raw data")
                return False

            # Patch the element
            self._patch_element_at_offset(
                raw_data,
                offset,
                orig_elem,
                imported_elem
            )

            patched_count += 1

        if self.verbose:
            print(f"  ✓ Patched {patched_count} elements")

        return True

    def _find_element_offset(
        self,
        raw_data: bytearray,
        element: Any
    ) -> Optional[int]:
        """
        Find the byte offset of an element in raw data.

        Args:
            raw_data: Raw binary data
            element: UnityPy element object

        Returns:
            Byte offset or None if not found
        """
        # Search for element ID
        id_bytes = struct.pack('<i', element.m_Id)
        offset = raw_data.find(id_bytes)

        if offset == -1:
            if self.verbose:
                print(
                    f"    DEBUG: Element {element.m_Id} - ID not found in binary")
            return None

        # Verify this is actually the element by checking neighbors
        if offset + 12 <= len(raw_data):
            order = struct.unpack('<i', raw_data[offset+4:offset+8])[0]
            parent = struct.unpack('<i', raw_data[offset+8:offset+12])[0]

            if self.verbose:
                print(f"    DEBUG: Element {element.m_Id} at offset {offset}")
                print(f"      Binary: order={order}, parent={parent}")
                print(
                    f"      Element: order={element.m_OrderInDocument}, parent={element.m_ParentId}")

            # OrderInDocument and ParentId should match
            if order == element.m_OrderInDocument and parent == element.m_ParentId:
                return offset
            else:
                if self.verbose:
                    print(f"      → Validation FAILED")

        return None

    def _patch_element_at_offset(
        self,
        raw_data: bytearray,
        offset: int,
        original: Any,
        imported: Dict[str, Any]
    ):
        """
        Patch element fields at a specific offset.

        Args:
            raw_data: Raw binary data to modify
            offset: Byte offset of element
            original: Original element object
            imported: Imported element dict
        """
        # Patch integer fields
        if self.verbose and original.m_Id in [1752032402, -753365010]:
            print(f"      Imported: {imported}")

        # m_Id at offset+0
        if 'm_Id' in imported:
            struct.pack_into('<i', raw_data, offset, imported['m_Id'])

        # m_OrderInDocument at offset+4
        if 'm_OrderInDocument' in imported:
            struct.pack_into('<i', raw_data, offset+4,
                             imported['m_OrderInDocument'])

        # m_ParentId at offset+8
        if 'm_ParentId' in imported:
            struct.pack_into('<i', raw_data, offset+8, imported['m_ParentId'])

        # m_RuleIndex at offset+12
        if 'm_RuleIndex' in imported:
            rule_index = imported['m_RuleIndex']
            # Handle -1 as 0xFFFFFFFF
            if rule_index == -1:
                rule_index = 0xFFFFFFFF
            struct.pack_into('<I', raw_data, offset+12, rule_index)

        # Note: String fields (m_Type, m_Name, m_Classes) are stored elsewhere
        # in Unity's string table. Changing them requires more complex patching.
        # For now, we only support patching integer fields.

        if self.verbose:
            print(
                f"    Patched element {imported.get('m_Id', original.m_Id)} at offset {offset}")


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

    # Import XML
    importer = UXMLImporter()
    imported_data = importer.parse_uxml_file(xml_path)

    if imported_data is None:
        print(f"✗ Failed to parse XML: {xml_path}")
        return False

    # Check for errors (validation happens in parse_uxml_file)
    if importer.errors:
        print(f"✗ XML validation failed:")
        for error in importer.errors:
            print(f"  {error.severity.upper()}: {error.message}")
        return False

    # Patch
    patcher = UXMLBinaryPatcher()
    patcher.verbose = verbose

    return patcher.patch_uxml_asset(
        bundle_path,
        asset_name,
        imported_data,
        output_path
    )
