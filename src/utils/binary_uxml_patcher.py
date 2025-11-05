"""
Binary UXML Patcher - Direct bundle modification bypassing UnityPy serialization.

This module patches UXML data at the binary level, avoiding UnityPy's
type tree serialization issues with UnknownObject types.
"""

import struct
import io
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path


class BinaryUXMLPatcher:
    """Patch UXML data directly in bundle binary format."""

    def __init__(self, bundle_data: bytes):
        """
        Initialize with raw bundle data.

        Args:
            bundle_data: Raw bytes of the Unity bundle
        """
        self.bundle_data = bytearray(bundle_data)
        self.patches: List[Tuple[int, bytes]] = []

    def find_asset_offset(self, asset_name: str) -> Optional[int]:
        """
        Find the byte offset of an asset by name in the bundle.

        Args:
            asset_name: Name of the asset to find

        Returns:
            Byte offset or None if not found
        """
        # Convert name to bytes (Unity uses UTF-8)
        name_bytes = asset_name.encode('utf-8')

        # Search for the name in the bundle
        offset = self.bundle_data.find(name_bytes)

        if offset == -1:
            return None

        return offset

    def read_int32(self, offset: int) -> int:
        """Read a 32-bit integer at offset."""
        return struct.unpack('<i', self.bundle_data[offset:offset+4])[0]

    def write_int32(self, offset: int, value: int):
        """Write a 32-bit integer at offset."""
        self.bundle_data[offset:offset+4] = struct.pack('<i', value)
        self.patches.append((offset, struct.pack('<i', value)))

    def read_int64(self, offset: int) -> int:
        """Read a 64-bit integer at offset."""
        return struct.unpack('<q', self.bundle_data[offset:offset+8])[0]

    def write_int64(self, offset: int, value: int):
        """Write a 64-bit integer at offset."""
        self.bundle_data[offset:offset+8] = struct.pack('<q', value)
        self.patches.append((offset, struct.pack('<q', value)))

    def read_string(self, offset: int) -> Tuple[str, int]:
        """
        Read a Unity string (length-prefixed).

        Returns:
            Tuple of (string, bytes_read)
        """
        # Unity strings are length-prefixed with a variable-length int
        length, bytes_read = self.read_varint(offset)

        if length == 0:
            return "", bytes_read

        string_offset = offset + bytes_read
        string_bytes = self.bundle_data[string_offset:string_offset+length]

        return string_bytes.decode('utf-8'), bytes_read + length

    def read_varint(self, offset: int) -> Tuple[int, int]:
        """
        Read a variable-length integer (Unity's compact format).

        Returns:
            Tuple of (value, bytes_read)
        """
        value = 0
        shift = 0
        bytes_read = 0

        while True:
            byte = self.bundle_data[offset + bytes_read]
            bytes_read += 1

            value |= (byte & 0x7F) << shift

            if (byte & 0x80) == 0:
                break

            shift += 7

        return value, bytes_read

    def write_varint(self, offset: int, value: int) -> int:
        """
        Write a variable-length integer.

        Returns:
            Number of bytes written
        """
        bytes_written = 0

        while value > 0x7F:
            self.bundle_data[offset + bytes_written] = (value & 0x7F) | 0x80
            bytes_written += 1
            value >>= 7

        self.bundle_data[offset + bytes_written] = value & 0x7F
        bytes_written += 1

        return bytes_written

    def patch_element_property(self, element_offset: int, property_name: str,
                               new_value: Any) -> bool:
        """
        Patch a specific property of a visual element.

        Args:
            element_offset: Byte offset of the element in the bundle
            property_name: Name of the property to patch (e.g., 'm_Id', 'm_Name')
            new_value: New value for the property

        Returns:
            True if patched successfully
        """
        # This requires understanding Unity's binary format for elements
        # For now, implement basic int32 patching

        if property_name == 'm_Id':
            # m_Id is typically at a fixed offset within the element structure
            # Need to determine this from Unity's serialization format
            self.write_int32(element_offset, new_value)
            return True

        return False

    def get_modified_bundle(self) -> bytes:
        """
        Get the modified bundle data.

        Returns:
            Modified bundle as bytes
        """
        return bytes(self.bundle_data)

    def save_to_file(self, output_path: Path):
        """Save the modified bundle to a file."""
        output_path.write_bytes(self.get_modified_bundle())


class SmartUXMLPatcher:
    """
    Smart UXML patcher that uses UnityPy for reading but custom binary
    writing for modified data.
    """

    def __init__(self, bundle_path: Path):
        """
        Initialize with bundle path.

        Args:
            bundle_path: Path to the Unity bundle file
        """
        self.bundle_path = bundle_path
        self.bundle_data = bundle_path.read_bytes()
        self.binary_patcher = BinaryUXMLPatcher(self.bundle_data)

    def patch_uxml_asset(self, asset_name: str, uxml_data: Dict[str, Any]) -> bool:
        """
        Patch a UXML asset using a hybrid approach:
        1. Use UnityPy to read and locate the asset
        2. Calculate what needs to change
        3. Apply changes directly to binary data

        Args:
            asset_name: Name of the asset to patch
            uxml_data: New UXML data

        Returns:
            True if successful
        """
        import UnityPy

        # Load with UnityPy to get structure info
        env = UnityPy.load(str(self.bundle_path))

        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue

            try:
                data = obj.read()

                if not hasattr(data, 'm_Name') or data.m_Name != asset_name:
                    continue

                if not hasattr(data, 'm_VisualElementAssets'):
                    continue

                # Found the asset!
                # Get the byte offset from UnityPy
                byte_start = obj.byte_start
                byte_size = obj.byte_size

                print(
                    f"Found asset at offset: {byte_start}, size: {byte_size}")

                # Strategy: Rebuild the entire asset in binary format
                # and replace the section in the bundle
                new_asset_data = self._serialize_visual_tree_asset(
                    data, uxml_data)

                if len(new_asset_data) <= byte_size:
                    # Can fit in existing space - direct replacement
                    self.binary_patcher.bundle_data[byte_start:byte_start+len(
                        new_asset_data)] = new_asset_data

                    # Pad with zeros if smaller
                    if len(new_asset_data) < byte_size:
                        padding = byte_size - len(new_asset_data)
                        self.binary_patcher.bundle_data[byte_start+len(
                            new_asset_data):byte_start+byte_size] = b'\x00' * padding

                    return True
                else:
                    print(
                        f"Warning: New asset ({len(new_asset_data)} bytes) larger than original ({byte_size} bytes)")
                    # Would need to relocate asset or rebuild bundle
                    return False

            except Exception as e:
                continue

        return False

    def _serialize_visual_tree_asset(self, original_data: Any, uxml_data: Dict[str, Any]) -> bytes:
        """
        Serialize a VisualTreeAsset to Unity's binary format.

        This is the key function - we manually recreate Unity's binary format.

        Args:
            original_data: Original UnityPy data object (for reference)
            uxml_data: New data to serialize

        Returns:
            Binary representation of the asset
        """
        buffer = io.BytesIO()

        # Unity's MonoBehaviour serialization format:
        # 1. Script reference (PPtr)
        # 2. m_Name (string)
        # 3. Object fields in order

        # Write m_Name
        name = getattr(original_data, 'm_Name', '')
        self._write_string(buffer, name)

        # Write m_VisualElementAssets (array)
        elements = uxml_data.get('m_VisualElementAssets', [])
        self._write_array(buffer, elements, self._write_visual_element)

        # Write m_UxmlObjectAssets (array)
        object_assets = uxml_data.get('m_UxmlObjectAssets', [])
        self._write_array(buffer, object_assets, self._write_uxml_object)

        # Write managedReferencesRegistry
        if 'managedReferencesRegistry' in uxml_data:
            self._write_managed_references(
                buffer, uxml_data['managedReferencesRegistry'])

        return buffer.getvalue()

    def _write_string(self, buffer: io.BytesIO, value: str):
        """Write a Unity string."""
        if not value:
            buffer.write(struct.pack('<I', 0))
            return

        encoded = value.encode('utf-8')
        buffer.write(struct.pack('<I', len(encoded)))
        buffer.write(encoded)

        # Unity aligns strings to 4-byte boundaries
        padding = (4 - (len(encoded) % 4)) % 4
        buffer.write(b'\x00' * padding)

    def _write_array(self, buffer: io.BytesIO, items: List, item_writer):
        """Write a Unity array."""
        buffer.write(struct.pack('<I', len(items)))

        for item in items:
            item_writer(buffer, item)

    def _write_visual_element(self, buffer: io.BytesIO, elem: Dict):
        """Write a VisualElementAsset."""
        # Based on Unity's VisualElementAsset structure
        buffer.write(struct.pack('<i', elem.get('m_Id', 0)))
        buffer.write(struct.pack('<i', elem.get('m_OrderInDocument', 0)))
        buffer.write(struct.pack('<i', elem.get('m_ParentId', 0)))
        buffer.write(struct.pack('<i', elem.get('m_RuleIndex', -1)))

        # m_Type (string)
        self._write_string(buffer, elem.get('m_Type', ''))

        # m_Name (string)
        self._write_string(buffer, elem.get('m_Name', ''))

        # m_Classes (array of strings)
        classes = elem.get('m_Classes', [])
        buffer.write(struct.pack('<I', len(classes)))
        for cls in classes:
            self._write_string(buffer, cls)

    def _write_uxml_object(self, buffer: io.BytesIO, obj: Dict):
        """Write a UxmlObjectAsset."""
        # Implement based on Unity's format
        pass

    def _write_managed_references(self, buffer: io.BytesIO, registry: Dict):
        """Write managed references registry."""
        buffer.write(struct.pack('<I', registry.get('version', 2)))

        # RefIds
        ref_ids = registry.get('RefIds', [])
        buffer.write(struct.pack('<I', len(ref_ids)))
        for rid in ref_ids:
            buffer.write(struct.pack('<I', rid))

        # References (complex nested structures)
        refs = registry.get('references', [])
        buffer.write(struct.pack('<I', len(refs)))

        for ref in refs:
            self._write_managed_reference(buffer, ref)

    def _write_managed_reference(self, buffer: io.BytesIO, ref: Dict):
        """Write a single managed reference."""
        # Type info
        type_info = ref.get('type', {})
        self._write_string(buffer, type_info.get('class', ''))
        self._write_string(buffer, type_info.get('ns', ''))
        self._write_string(buffer, type_info.get('asm', ''))

        # Data (varies by type)
        data = ref.get('data', {})

        # uxmlAssetId
        buffer.write(struct.pack('<i', data.get('uxmlAssetId', 0)))

        # Additional fields depend on the binding type
        # This would need to be expanded based on each binding type

    def save(self, output_path: Path):
        """Save the patched bundle."""
        self.binary_patcher.save_to_file(output_path)
