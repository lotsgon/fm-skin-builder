"""Parse and manipulate individual UXML element binary structures."""

import struct
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class UXMLElementBinary:
    """Represents a UXML element's binary structure."""
    # Fixed fields (16 bytes)
    m_Id: int
    m_OrderInDocument: int
    m_ParentId: int
    m_RuleIndex: int

    # UI behavior fields (20 bytes at offset +16-35)
    m_PickingMode: int            # Offset +16: UI picking mode (0 = Position)
    m_SkipClone: int              # Offset +20: Skip clone flag (0 = false)
    m_XmlNamespace: int           # Offset +24: Namespace reference (always -1)
    unknown_field_1: int          # Offset +28: Unknown (always 0)
    unknown_field_2: int          # Offset +32: Unknown (always 0)

    # Variable string arrays
    m_Classes: List[str]
    m_StylesheetPaths: List[str]

    # Serialization fields (16 bytes after m_StylesheetPaths)
    unknown_field_3: int          # Always 0
    m_SerializedData: int         # Reference ID for binding data (rid value)
    unknown_field_4: int          # Varies: -1 or 0
    unknown_field_5: int          # Always 0

    # Element type and name
    m_Type: str
    m_Name: str

    # Original offset in file
    offset: int
    # Original size in bytes (as parsed from binary)
    original_size: int = 0

    def __len__(self) -> int:
        """Calculate total size of this element in bytes."""
        size = 16  # Fixed integer fields
        size += 20  # UI behavior fields (5 int32s)
        size += 4  # m_Classes array size

        # Add size of each class string (NO null, NO per-string alignment)
        for class_name in self.m_Classes:
            size += 4  # String length field
            str_len = len(class_name.encode('utf-8'))
            size += str_len  # String data only

        # Align entire m_Classes array to 4-byte boundary
        remainder = size % 4
        if remainder != 0:
            size += 4 - remainder

        size += 4  # m_StylesheetPaths array size

        # Add size of each path string (NO null, NO per-string alignment)
        for path in self.m_StylesheetPaths:
            size += 4  # String length field
            str_len = len(path.encode('utf-8'))
            size += str_len  # String data only

        # Align entire m_StylesheetPaths array to 4-byte boundary
        remainder = size % 4
        if remainder != 0:
            size += 4 - remainder

        size += 16  # Serialization fields (4 int32s)

        # m_Type string (4-byte aligned)
        size += 4  # String length field
        type_len = len(self.m_Type.encode('utf-8'))
        size += type_len + 1  # String data + null terminator
        # Align to 4-byte boundary
        remainder = (size) % 4
        if remainder != 0:
            size += 4 - remainder

        # m_Name string (NOT aligned - last field)
        size += 4  # String length field
        name_len = len(self.m_Name.encode('utf-8'))
        size += name_len + 1  # String data + null terminator

        return size

    def to_bytes(self) -> bytes:
        """Serialize element back to binary format."""
        data = bytearray()

        # Fixed integer fields
        data.extend(struct.pack('<i', self.m_Id))
        data.extend(struct.pack('<i', self.m_OrderInDocument))
        data.extend(struct.pack('<i', self.m_ParentId))

        # Handle m_RuleIndex as unsigned if it was -1
        if self.m_RuleIndex == -1:
            data.extend(struct.pack('<I', 0xFFFFFFFF))
        else:
            data.extend(struct.pack('<i', self.m_RuleIndex))

        # UI behavior fields (20 bytes)
        data.extend(struct.pack('<i', self.m_PickingMode))
        data.extend(struct.pack('<i', self.m_SkipClone))
        data.extend(struct.pack('<i', self.m_XmlNamespace))
        data.extend(struct.pack('<i', self.unknown_field_1))
        data.extend(struct.pack('<i', self.unknown_field_2))

        # m_Classes array
        data.extend(struct.pack('<i', len(self.m_Classes)))
        for class_name in self.m_Classes:
            class_bytes = class_name.encode('utf-8')
            data.extend(struct.pack('<i', len(class_bytes)))
            data.extend(class_bytes)

            # Conditional null terminator + alignment
            # If string ends on 4-byte boundary, no null needed
            if len(data) % 4 == 0:
                # Already aligned, no null
                pass
            else:
                # Add null and pad to align
                data.append(0)
                while len(data) % 4 != 0:
                    data.append(0)

        # m_StylesheetPaths array
        data.extend(struct.pack('<i', len(self.m_StylesheetPaths)))
        for path in self.m_StylesheetPaths:
            path_bytes = path.encode('utf-8')
            data.extend(struct.pack('<i', len(path_bytes)))
            data.extend(path_bytes)

            # Conditional null terminator + alignment
            # If string ends on 4-byte boundary, no null needed
            if len(data) % 4 == 0:
                # Already aligned, no null
                pass
            else:
                # Add null and pad to align
                data.append(0)
                while len(data) % 4 != 0:
                    data.append(0)

        # Serialization fields (16 bytes - 4 fields)
        data.extend(struct.pack('<i', self.unknown_field_3))
        data.extend(struct.pack('<i', self.m_SerializedData))
        data.extend(struct.pack('<i', self.unknown_field_4))
        data.extend(struct.pack('<i', self.unknown_field_5))

        # m_Type string
        type_bytes = self.m_Type.encode('utf-8')
        data.extend(struct.pack('<i', len(type_bytes)))
        data.extend(type_bytes)
        data.append(0)  # Null terminator
        # Align to 4-byte boundary
        while len(data) % 4 != 0:
            data.append(0)

        # m_Name string (last field, not aligned)
        name_bytes = self.m_Name.encode('utf-8')
        data.extend(struct.pack('<i', len(name_bytes)))
        data.extend(name_bytes)
        data.append(0)  # Null terminator

        return bytes(data)


def parse_element_at_offset(raw_data: bytes, offset: int, debug: bool = False) -> Optional[UXMLElementBinary]:
    """
    Parse a UXML element from raw binary data.

    Args:
        raw_data: Complete raw asset data
        offset: Byte offset where element starts
        debug: Enable debug output

    Returns:
        Parsed element or None if parsing fails
    """
    try:
        # Read fixed fields
        m_id = struct.unpack_from('<i', raw_data, offset)[0]
        m_order = struct.unpack_from('<i', raw_data, offset + 4)[0]
        m_parent = struct.unpack_from('<i', raw_data, offset + 8)[0]
        m_rule = struct.unpack_from('<I', raw_data, offset + 12)[0]

        if debug:
            print(f"DEBUG: Parsing element at offset {offset}")
            print(f"  m_Id: {m_id}, m_Order: {m_order}, m_Parent: {m_parent}, m_Rule: {m_rule}")

        # Handle -1 as 0xFFFFFFFF
        if m_rule == 0xFFFFFFFF:
            m_rule = -1

        # Read UI behavior fields (bytes 16-35, total 20 bytes = 5 int32s)
        m_picking_mode = struct.unpack_from('<i', raw_data, offset + 16)[0]
        m_skip_clone = struct.unpack_from('<i', raw_data, offset + 20)[0]
        m_xml_namespace = struct.unpack_from('<i', raw_data, offset + 24)[0]
        unknown_field_1 = struct.unpack_from('<i', raw_data, offset + 28)[0]
        unknown_field_2 = struct.unpack_from('<i', raw_data, offset + 32)[0]

        # m_Classes array starts at offset +36
        pos = offset + 36

        # Helper function to read a string array
        def read_string_array(pos, array_name):
            """Read a Unity string array with 4-byte alignment."""
            if pos + 4 > len(raw_data):
                if debug:
                    print(f"DEBUG: Not enough data to read {array_name} count at {pos}")
                return None, pos

            count = struct.unpack_from('<i', raw_data, pos)[0]
            pos += 4

            if debug:
                print(f"  {array_name} count: {count} at pos {pos-4}")

            # Sanity check
            if count < 0 or count > 100:
                if debug:
                    print(f"DEBUG: Unreasonable {array_name} count: {count}")
                return None, pos

            strings = []
            for i in range(count):
                if pos + 4 > len(raw_data):
                    if debug:
                        print(f"DEBUG: Not enough data to read {array_name}[{i}] length at {pos}")
                    return None, pos

                str_len = struct.unpack_from('<i', raw_data, pos)[0]
                pos += 4

                if debug:
                    print(f"  {array_name}[{i}]: length={str_len} at pos {pos-4}")

                # Sanity check on string length
                if str_len < 0 or str_len > 1000:
                    if debug:
                        print(f"DEBUG: Unreasonable string length: {str_len}")
                    return None, pos

                if pos + str_len + 1 > len(raw_data):
                    if debug:
                        print(f"DEBUG: Not enough data to read {array_name}[{i}] string at {pos}")
                    return None, pos

                # Read string bytes
                str_bytes = raw_data[pos:pos + str_len]
                try:
                    string_val = str_bytes.decode('utf-8')
                    strings.append(string_val)
                    if debug:
                        print(f"    decoded: '{string_val}'")
                except UnicodeDecodeError as e:
                    if debug:
                        print(f"DEBUG: Failed to decode {array_name} string at pos {pos}: {e}")
                        print(f"  Bytes: {str_bytes[:20]}")
                    return None, pos

                pos += str_len

                # Conditional null terminator + alignment
                # If string ends on 4-byte boundary, no null needed
                # Otherwise, add null and pad to 4-byte boundary
                if pos % 4 == 0:
                    # Already aligned, no null needed
                    if debug and i < count - 1:
                        print("    string ends aligned, no null needed")
                else:
                    # Add null terminator
                    pos += 1
                    if debug:
                        print(f"    added null terminator at {pos-1}")

                    # Pad to 4-byte boundary if needed
                    remainder = pos % 4
                    if remainder != 0:
                        padding = 4 - remainder
                        pos += padding
                        if debug and i < count - 1:
                            print(f"    added {padding} bytes padding to align to {pos}")

            if debug:
                print(f"  {array_name} array ends at pos {pos}")

            return strings, pos

        # Read m_Classes array
        classes, pos = read_string_array(pos, "m_Classes")
        if classes is None:
            return None

        # Read m_StylesheetPaths array
        paths, pos = read_string_array(pos, "m_StylesheetPaths")
        if paths is None:
            return None

        # Read serialization fields (16 bytes = 4 int32s)
        if pos + 16 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read serialization fields at {pos}")
            return None

        unknown_field_3 = struct.unpack_from('<i', raw_data, pos)[0]
        m_serialized_data = struct.unpack_from('<i', raw_data, pos + 4)[0]
        unknown_field_4 = struct.unpack_from('<i', raw_data, pos + 8)[0]
        unknown_field_5 = struct.unpack_from('<i', raw_data, pos + 12)[0]
        pos += 16

        if debug:
            print(f"  serialization fields: ({unknown_field_3}, {m_serialized_data}, {unknown_field_4}, {unknown_field_5}) at pos {pos-16}")

        # Read m_Type string (4-byte aligned) - length field is next
        if pos + 4 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read m_Type length at {pos}")
            return None

        type_len = struct.unpack_from('<i', raw_data, pos)[0]
        pos += 4

        if debug:
            print(f"  m_Type length: {type_len} at pos {pos-4}")

        if type_len < 0 or type_len > 1000:
            if debug:
                print(f"DEBUG: Unreasonable m_Type length: {type_len}")
            return None

        if pos + type_len + 1 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read m_Type string at {pos}")
            return None

        type_bytes = raw_data[pos:pos + type_len]
        try:
            m_type = type_bytes.decode('utf-8')
            if debug:
                print(f"    m_Type: '{m_type}'")
        except UnicodeDecodeError as e:
            if debug:
                print(f"DEBUG: Failed to decode m_Type at pos {pos}: {e}")
            return None

        pos += type_len + 1  # +1 for null terminator

        # Align to 4-byte boundary
        remainder = pos % 4
        if remainder != 0:
            padding = 4 - remainder
            pos += padding
            if debug:
                print(f"    added {padding} bytes of padding after m_Type, now at pos {pos}")

        # Read m_Name string (NOT aligned - last field)
        if pos + 4 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read m_Name length at {pos}")
            return None

        name_len = struct.unpack_from('<i', raw_data, pos)[0]
        pos += 4

        if debug:
            print(f"  m_Name length: {name_len} at pos {pos-4}")

        if name_len < 0 or name_len > 1000:
            if debug:
                print(f"DEBUG: Unreasonable m_Name length: {name_len}")
            return None

        if pos + name_len + 1 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read m_Name string at {pos}")
            return None

        name_bytes = raw_data[pos:pos + name_len]
        try:
            m_name = name_bytes.decode('utf-8')
            if debug:
                print(f"    m_Name: '{m_name}'")
        except UnicodeDecodeError as e:
            if debug:
                print(f"DEBUG: Failed to decode m_Name at pos {pos}: {e}")
            return None

        pos += name_len + 1  # +1 for null terminator

        # Calculate original size (from start offset to end position)
        original_size = pos - offset

        if debug:
            print(f"  Element parsing complete, ended at pos {pos}")
            print(f"  Original size: {original_size} bytes")

        return UXMLElementBinary(
            m_Id=m_id,
            m_OrderInDocument=m_order,
            m_ParentId=m_parent,
            m_RuleIndex=m_rule,
            m_PickingMode=m_picking_mode,
            m_SkipClone=m_skip_clone,
            m_XmlNamespace=m_xml_namespace,
            unknown_field_1=unknown_field_1,
            unknown_field_2=unknown_field_2,
            m_Classes=classes,
            m_StylesheetPaths=paths,
            unknown_field_3=unknown_field_3,
            m_SerializedData=m_serialized_data,
            unknown_field_4=unknown_field_4,
            unknown_field_5=unknown_field_5,
            m_Type=m_type,
            m_Name=m_name,
            offset=offset,
            original_size=original_size
        )

    except Exception as e:
        print(f"Error parsing element at offset {offset}: {e}")
        return None


def find_element_offset(raw_data: bytes, element_id: int, start_offset: int = 0) -> int:
    """
    Find the byte offset of an element by its ID.

    Args:
        raw_data: Complete raw asset data
        element_id: m_Id to search for
        start_offset: Where to start searching

    Returns:
        Byte offset or -1 if not found
    """
    target_bytes = struct.pack('<i', element_id)
    offset = raw_data.find(target_bytes, start_offset)

    # Verify this is actually an element start by checking structure
    if offset != -1 and offset + 12 < len(raw_data):
        # Check if next 8 bytes look like m_OrderInDocument and m_ParentId
        order = struct.unpack_from('<i', raw_data, offset + 4)[0]

        # Heuristic: order should be reasonable (0-10000)
        if 0 <= order < 10000:
            return offset

    # Try searching for next occurrence
    if offset != -1:
        return find_element_offset(raw_data, element_id, offset + 4)

    return -1


def rebuild_element_section(elements: List[UXMLElementBinary]) -> bytes:
    """
    Rebuild a section of UXML elements with potentially modified data.

    This handles variable-length elements properly.

    Args:
        elements: List of elements to serialize

    Returns:
        Binary data for all elements
    """
    data = bytearray()
    for elem in elements:
        data.extend(elem.to_bytes())
    return bytes(data)
