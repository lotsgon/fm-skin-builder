#!/usr/bin/env python3
"""Trace TypeTree reading to find where it fails."""

import UnityPy
from UnityPy.streams import EndianBinaryReader

# Load generated data
with open('/tmp/generated_vta.bin', 'rb') as f:
    generated_data = f.read()

print(f'Generated data size: {len(generated_data)} bytes')
print()

# Load original to get TypeTree
env = UnityPy.load('test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle')

for obj in env.objects:
    if obj.type.name == 'MonoBehaviour':
        try:
            if obj.peek_name() == 'AboutClubCard':
                # Get TypeTree
                node = obj._get_typetree_node()

                # Create a custom reader that tracks position
                reader = EndianBinaryReader(generated_data, endian=obj.reader.endian)

                print("TypeTree top-level fields:")
                for i, child in enumerate(node.m_Children):
                    print(f"  {i}. {child.m_Name} ({child.m_Type})")

                print()
                print("Attempting manual field-by-field read...")
                print()

                # Try to read each field manually
                from UnityPy.helpers import TypeTreeHelper
                from UnityPy.helpers.TypeTreeHelper import TypeTreeConfig

                config = TypeTreeConfig(as_dict=False, assetsfile=obj.assets_file)
                reader.Position = 0
                for i, child in enumerate(node.m_Children):
                    pos_before = reader.Position
                    try:
                        # Read this specific field
                        value = TypeTreeHelper.read_value(child, reader, config)
                        pos_after = reader.Position
                        bytes_read = pos_after - pos_before

                        # Get a summary of the value
                        if isinstance(value, list):
                            summary = f"array with {len(value)} elements"
                        elif isinstance(value, dict):
                            summary = f"dict with {len(value)} keys"
                        elif isinstance(value, str):
                            summary = f'"{value[:30]}..."' if len(value) > 30 else f'"{value}"'
                        else:
                            summary = str(value)

                        print(f"✓ Field {i} ({child.m_Name}): {bytes_read} bytes, value: {summary}")

                    except Exception as e:
                        pos_after = reader.Position
                        bytes_read = pos_after - pos_before
                        print(f"✗ Field {i} ({child.m_Name}): FAILED after {bytes_read} bytes at position {pos_after}")
                        print(f"  Error: {e}")
                        print(f"  Reader position: {reader.Position}")
                        print(f"  Data remaining: {len(generated_data) - reader.Position} bytes")

                        # Show context
                        if reader.Position < len(generated_data):
                            print("  Next 32 bytes:")
                            for j in range(reader.Position, min(reader.Position + 32, len(generated_data)), 16):
                                hex_str = ' '.join(f'{b:02x}' for b in generated_data[j:j+16])
                                print(f"    {j:04d}: {hex_str}")
                        break

                break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
