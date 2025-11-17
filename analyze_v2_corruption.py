#!/usr/bin/env python3
"""Analyze where V2 binary format causes read_str error."""

import UnityPy
from fm_skin_builder.core.uxml.uxml_element_parser import parse_element_at_offset

# Load V2 bundle
v2_env = UnityPy.load('test_output/ui-panelids-uxml_assets_all_v2.bundle')

for obj in v2_env.objects:
    if obj.type.name == 'MonoBehaviour':
        try:
            if obj.peek_name() == 'AboutClubCard':
                v2_raw = obj.get_raw_data()
                print(f'Found AboutClubCard V2: {len(v2_raw)} bytes\n')

                # Try to parse each element manually
                print('Parsing visual elements:')
                print('='*80)

                # Element 1: offset 196
                print('\nElement 1 at offset 196:')
                try:
                    elem1 = parse_element_at_offset(v2_raw, 196, debug=True)
                    print('✅ Element 1 parsed successfully')
                    print(f'   Ended at offset: {elem1.offset + len(elem1)}')
                except Exception as e:
                    print(f'❌ Error parsing element 1: {e}')
                    import traceback
                    traceback.print_exc()

                # Element 2: should be at 292 in original, but might be different now
                # Calculate where it should be
                if elem1:
                    elem1_end = elem1.offset + len(elem1)
                    padding = (4 - (elem1_end % 4)) % 4
                    elem2_offset = elem1_end + padding

                    print(f'\nElement 2 should start at offset {elem2_offset}:')
                    try:
                        elem2 = parse_element_at_offset(v2_raw, elem2_offset, debug=True)
                        print('✅ Element 2 parsed successfully')
                        print(f'   Ended at offset: {elem2.offset + len(elem2)}')
                    except Exception as e:
                        print(f'❌ Error parsing element 2: {e}')
                        import traceback
                        traceback.print_exc()

                # Now try to have UnityPy read the object
                print('\n' + '='*80)
                print('Attempting UnityPy read():')
                print('='*80)
                try:
                    data = obj.read()
                    print('✅ UnityPy read() succeeded!')
                except Exception as e:
                    print(f'❌ UnityPy read() failed: {e}')
                    import traceback
                    traceback.print_exc()

                break
        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
            break
