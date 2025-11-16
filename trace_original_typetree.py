#!/usr/bin/env python3
"""Trace TypeTree reading on ORIGINAL data."""

import UnityPy
from pathlib import Path
from UnityPy.streams import EndianBinaryReader
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.TypeTreeHelper import TypeTreeConfig

# Load original bundle
env = UnityPy.load('test_skin_dir/packages/ui-panelids-uxml_assets_all.bundle')

for obj in env.objects:
    if obj.type.name == 'MonoBehaviour':
        try:
            if obj.peek_name() == 'AboutClubCard':
                # Get raw data and TypeTree
                raw_data = obj.get_raw_data()
                node = obj._get_typetree_node()

                print(f'Original data size: {len(raw_data)} bytes')
                print()

                # Create reader
                reader = EndianBinaryReader(raw_data, endian=obj.reader.endian)
                config = TypeTreeConfig(as_dict=False, assetsfile=obj.assets_file)

                # Read field-by-field
                reader.Position = 0
                for i, child in enumerate(node.m_Children):
                    pos_before = reader.Position
                    try:
                        value = TypeTreeHelper.read_value(child, reader, config)
                        pos_after = reader.Position
                        bytes_read = pos_after - pos_before

                        # Summary
                        if isinstance(value, list):
                            summary = f"array with {len(value)} elements"
                        elif isinstance(value, dict):
                            summary = f"dict with {len(value)} keys"
                        elif isinstance(value, str):
                            summary = f'"{value[:30]}..."' if len(value) > 30 else f'"{value}"'
                        else:
                            summary = str(value)

                        print(f"✓ Field {i:2d} ({child.m_Name:30s}): {bytes_read:5d} bytes @ offset {pos_before:5d}, value: {summary}")

                    except Exception as e:
                        pos_after = reader.Position
                        bytes_read = pos_after - pos_before
                        print(f"✗ Field {i} ({child.m_Name}): FAILED after {bytes_read} bytes at position {pos_after}")
                        print(f"  Error: {e}")
                        break

                print()
                print(f"Total bytes read: {reader.Position}")
                print(f"Bytes remaining: {len(raw_data) - reader.Position}")

                break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
