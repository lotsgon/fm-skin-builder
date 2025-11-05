"""
CSS Class Patcher - Modify m_Classes arrays in UXML elements.

This is a focused patcher that ONLY modifies CSS classes, leaving everything else intact.
It handles variable-length string arrays properly by shifting subsequent data.
"""

import struct
from typing import List, Tuple, Optional


class CSSClassPatcher:
    """Patch CSS classes in UXML element binary data."""

    @staticmethod
    def find_classes_offset(raw_data: bytes, element_offset: int) -> Tuple[int, List[str]]:
        """
        Find the m_Classes array in an element and parse current classes.

        Args:
            raw_data: Complete binary data
            element_offset: Offset where element starts

        Returns:
            Tuple of (classes_array_offset, current_classes)
        """
        # m_Classes array is at offset +36 from element start
        classes_offset = element_offset + 36

        # Read array size
        num_classes = struct.unpack_from('<i', raw_data, classes_offset)[0]
        pos = classes_offset + 4

        # Read existing classes
        classes = []
        for _ in range(num_classes):
            str_len = struct.unpack_from('<i', raw_data, pos)[0]
            pos += 4

            str_bytes = raw_data[pos:pos + str_len]
            try:
                class_name = str_bytes.decode('utf-8')
                classes.append(class_name)
            except UnicodeDecodeError:
                # Non-UTF8 data, probably read wrong offset
                return -1, []

            pos += str_len + 1  # +1 for null terminator

        return classes_offset, classes

    @staticmethod
    def calculate_classes_size(classes: List[str]) -> int:
        """Calculate byte size needed for a classes array."""
        size = 4  # Array size field
        for class_name in classes:
            size += 4  # String length field
            size += len(class_name.encode('utf-8'))  # String data
            size += 1  # Null terminator
        return size

    @staticmethod
    def encode_classes(classes: List[str]) -> bytes:
        """Encode classes array to binary format."""
        data = bytearray()
        data.extend(struct.pack('<i', len(classes)))

        for class_name in classes:
            class_bytes = class_name.encode('utf-8')
            data.extend(struct.pack('<i', len(class_bytes)))
            data.extend(class_bytes)
            data.append(0)  # Null terminator

        return bytes(data)

    @staticmethod
    def patch_classes(
        raw_data: bytes,
        element_offset: int,
        new_classes: List[str]
    ) -> Optional[bytes]:
        """
        Replace the m_Classes array in an element.

        This handles size changes by shifting subsequent data.

        Args:
            raw_data: Complete binary data
            element_offset: Offset where element starts
            new_classes: New list of CSS classes

        Returns:
            Modified binary data or None if patching fails
        """
        # Find current classes
        classes_offset, old_classes = CSSClassPatcher.find_classes_offset(
            raw_data, element_offset)

        if classes_offset == -1:
            return None

        # Calculate sizes
        old_size = CSSClassPatcher.calculate_classes_size(old_classes)
        new_size = CSSClassPatcher.calculate_classes_size(new_classes)
        size_diff = new_size - old_size

        # Encode new classes
        new_classes_bytes = CSSClassPatcher.encode_classes(new_classes)

        # Build modified data
        result = bytearray()

        # 1. Everything before the classes array
        result.extend(raw_data[:classes_offset])

        # 2. New classes array
        result.extend(new_classes_bytes)

        # 3. Everything after the old classes array
        old_classes_end = classes_offset + old_size
        result.extend(raw_data[old_classes_end:])

        return bytes(result)

    @staticmethod
    def swap_element_classes(
        raw_data: bytes,
        element_id_1: int,
        element_id_2: int
    ) -> Optional[bytes]:
        """
        Swap the CSS classes between two elements.

        This is useful for reordering UI elements while keeping their styling.

        Args:
            raw_data: Complete binary data
            element_id_1: First element's m_Id
            element_id_2: Second element's m_Id

        Returns:
            Modified binary data or None if patching fails
        """
        # Find both elements
        from .uxml_element_parser import find_element_offset

        offset1 = find_element_offset(raw_data, element_id_1)
        offset2 = find_element_offset(raw_data, element_id_2)

        if offset1 == -1 or offset2 == -1:
            return None

        # Get both classes arrays
        _, classes1 = CSSClassPatcher.find_classes_offset(raw_data, offset1)
        _, classes2 = CSSClassPatcher.find_classes_offset(raw_data, offset2)

        # Patch first element (order matters if sizes differ!)
        # Always patch the later element first to avoid offset invalidation
        if offset1 < offset2:
            # Patch element 2 first
            modified = CSSClassPatcher.patch_classes(
                raw_data, offset2, classes1)
            if not modified:
                return None

            # Now find element 1's new offset (it may have shifted)
            new_offset1 = find_element_offset(modified, element_id_1)
            if new_offset1 == -1:
                return None

            # Patch element 1
            modified = CSSClassPatcher.patch_classes(
                modified, new_offset1, classes2)
        else:
            # Patch element 1 first
            modified = CSSClassPatcher.patch_classes(
                raw_data, offset1, classes2)
            if not modified:
                return None

            # Find element 2's new offset
            new_offset2 = find_element_offset(modified, element_id_2)
            if new_offset2 == -1:
                return None

            # Patch element 2
            modified = CSSClassPatcher.patch_classes(
                modified, new_offset2, classes1)

        return modified


def test_class_swapping():
    """Test swapping classes between two elements."""
    import sys
    from pathlib import Path
    sys.path.insert(0, '/workspaces/fm-skin-builder')
    import UnityPy

    bundle = UnityPy.load('bundles/ui-tiles_assets_all.bundle')

    for obj in bundle.objects:
        if obj.type.name == 'MonoBehaviour':
            data = obj.read()
            if hasattr(data, 'm_Name') and data.m_Name == 'PlayerAttributesStandardBlock':
                raw = obj.get_raw_data()

                print("Original classes:")
                _, classes1 = CSSClassPatcher.find_classes_offset(raw, 6216)
                _, classes2 = CSSClassPatcher.find_classes_offset(raw, 6604)
                print(f"  Element -753365010: {classes1}")
                print(f"  Element 1752032402: {classes2}")

                # Swap classes
                print("\nSwapping classes...")
                modified = CSSClassPatcher.swap_element_classes(
                    raw, -753365010, 1752032402)

                if modified:
                    print("✓ Swap successful")

                    # Verify
                    from .uxml_element_parser import find_element_offset
                    new_offset1 = find_element_offset(modified, -753365010)
                    new_offset2 = find_element_offset(modified, 1752032402)

                    _, new_classes1 = CSSClassPatcher.find_classes_offset(
                        modified, new_offset1)
                    _, new_classes2 = CSSClassPatcher.find_classes_offset(
                        modified, new_offset2)

                    print(f"\nAfter swap:")
                    print(f"  Element -753365010: {new_classes1}")
                    print(f"  Element 1752032402: {new_classes2}")

                    print(
                        f"\n Size change: {len(raw)} → {len(modified)} ({len(modified) - len(raw):+d} bytes)")
                else:
                    print("✗ Swap failed")

                return


if __name__ == '__main__':
    test_class_swapping()
