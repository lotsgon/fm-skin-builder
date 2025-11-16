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

    # Unknown fields (20 bytes) - preserved as-is
    unknown_bytes: bytes  # bytes 16-35

    # Variable string arrays
    m_Classes: List[str]

    # Store rest of element data (m_Type, m_Name, etc.)
    remaining_bytes: bytes

    # Original offset in file
    offset: int

    def __len__(self) -> int:
        """Calculate total size of this element in bytes."""
        size = 16  # Fixed integer fields
        size += len(self.unknown_bytes)  # Unknown section
        size += 4  # m_Classes array size

        # Add size of each class string
        for class_name in self.m_Classes:
            size += 4  # String length field
            size += len(class_name.encode('utf-8')) + 1  # String data + null terminator

        size += len(self.remaining_bytes)
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

        # Unknown bytes section
        data.extend(self.unknown_bytes)

        # m_Classes array
        data.extend(struct.pack('<i', len(self.m_Classes)))
        for class_name in self.m_Classes:
            class_bytes = class_name.encode('utf-8')
            data.extend(struct.pack('<i', len(class_bytes)))
            data.extend(class_bytes)
            data.append(0)  # Null terminator

        # Rest of element
        data.extend(self.remaining_bytes)

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

        # Read unknown section (bytes 16-35, total 20 bytes)
        unknown_bytes = raw_data[offset + 16:offset + 36]

        # Read m_Classes array size at offset +36
        pos = offset + 36
        if pos + 4 > len(raw_data):
            if debug:
                print(f"DEBUG: Not enough data to read class array size at {pos}")
            return None

        num_classes = struct.unpack_from('<i', raw_data, pos)[0]
        pos += 4

        if debug:
            print(f"  num_classes: {num_classes} at pos {pos-4}")

        # Sanity check on number of classes
        if num_classes < 0 or num_classes > 100:
            if debug:
                print(f"DEBUG: Unreasonable number of classes: {num_classes}")
            return None

        # Read class strings
        classes = []
        for i in range(num_classes):
            if pos + 4 > len(raw_data):
                if debug:
                    print(f"DEBUG: Not enough data to read class {i} length at {pos}")
                return None

            str_len = struct.unpack_from('<i', raw_data, pos)[0]
            pos += 4

            if debug:
                print(f"  class {i}: length={str_len} at pos {pos-4}")

            # Sanity check on string length
            if str_len < 0 or str_len > 1000:
                if debug:
                    print(f"DEBUG: Unreasonable string length: {str_len}")
                return None

            if pos + str_len + 1 > len(raw_data):
                if debug:
                    print(f"DEBUG: Not enough data to read class {i} string at {pos}")
                return None

            # Read string bytes (+ null terminator)
            str_bytes = raw_data[pos:pos + str_len]
            try:
                class_name = str_bytes.decode('utf-8')
                classes.append(class_name)
                if debug:
                    print(f"    decoded: '{class_name}'")
            except UnicodeDecodeError as e:
                # If we can't decode, something went wrong with parsing
                if debug:
                    print(f"DEBUG: Failed to decode class string at pos {pos}: {e}")
                    print(f"  Bytes: {str_bytes[:20]}")
                return None

            pos += str_len + 1  # +1 for null terminator

            # Align to 4-byte boundary for next field
            remainder = pos % 4
            if remainder != 0:
                padding = 4 - remainder
                pos += padding
                if debug:
                    print(f"    added {padding} bytes of padding, now at pos {pos}")

        # For now, store everything else as remaining_bytes
        # We'd need to parse m_StylesheetPaths and m_Type, m_Name arrays too
        # but for class editing, we can treat them as opaque
        #
        # Find the next element to determine size
        # This is a simplified approach - in reality we need to know the full structure

        # For now, read a fixed amount of remaining data
        remaining_start = pos

        # Try to find the next element ID (next 4-byte aligned negative or large positive int)
        # This is a heuristic - not perfect but works for contiguous elements
        next_elem_offset = None
        for check_offset in range(pos + 100, len(raw_data) - 16, 4):
            potential_id = struct.unpack_from('<i', raw_data, check_offset)[0]
            # Check if this looks like an element ID (typically large or negative)
            if abs(potential_id) > 1000000:  # Heuristic
                next_elem_offset = check_offset
                break

        if next_elem_offset:
            remaining_bytes = raw_data[remaining_start:next_elem_offset]
        else:
            # Last element or couldn't find next - read reasonable amount
            remaining_bytes = raw_data[remaining_start:remaining_start + 200]

        return UXMLElementBinary(
            m_Id=m_id,
            m_OrderInDocument=m_order,
            m_ParentId=m_parent,
            m_RuleIndex=m_rule,
            unknown_bytes=unknown_bytes,
            m_Classes=classes,
            remaining_bytes=remaining_bytes,
            offset=offset
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
