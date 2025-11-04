#!/usr/bin/env python3
"""
Test script to extract binding data from UXML files.
This extracts the data bindings that connect UI elements to game data.
"""

import UnityPy
from pathlib import Path


def extract_binding_path(binding_obj):
    """Extract path from a BindingPath or BindingMethod object."""
    if not binding_obj or not hasattr(binding_obj, '__dict__'):
        return None

    binding_dict = binding_obj.__dict__

    # Direct path
    if 'm_path' in binding_dict:
        path = binding_dict['m_path']
        if path:
            return path

    # Direct binding within BindingMethod
    if 'm_direct' in binding_dict:
        direct = binding_dict['m_direct']
        if hasattr(direct, 'm_path'):
            path = direct.m_path
            if path:
                return path

    # Visual function binding
    if 'm_visualFunction' in binding_dict:
        vf = binding_dict['m_visualFunction']
        if hasattr(vf, '__dict__') and 'm_func' in vf.__dict__:
            func = vf.__dict__['m_func']
            return f"visualFunction({func})"

    return None


def extract_bindings_from_serialized_data(ref_data):
    """Extract all binding information from a serialized data object."""
    bindings = {}

    if not ref_data:
        return bindings

    # Common fields
    element_name = getattr(ref_data, 'name', '')

    # Check all attributes for binding data
    for attr in dir(ref_data):
        if attr.startswith('_'):
            continue

        val = getattr(ref_data, attr, None)

        # Look for binding attributes
        if 'binding' in attr.lower():
            path = extract_binding_path(val)
            if path:
                bindings[attr] = path

        # Special handling for BindingRemapper Mappings
        if attr == 'Mappings' and val:
            mappings = []
            for mapping in val[:20]:  # First 20 mappings
                from_val = getattr(mapping, 'from_', None)
                to_val = getattr(mapping, 'to', None)

                if from_val and to_val:
                    to_path = extract_binding_path(to_val)
                    if to_path:
                        mappings.append(f"{from_val} -> {to_path}")

            if mappings:
                bindings['Mappings'] = mappings

        # Special handling for BindingExpect Parameters
        if attr == 'Parameters' and val:
            params = []
            for param in val[:20]:  # First 20 parameters
                param_name = getattr(param, 'name', None)
                if param_name:
                    params.append(param_name)

            if params:
                bindings['Parameters'] = params

        # Special handling for BindingVariables
        if attr == 'ValueVariables' and val:
            variables = []
            for var in val[:20]:
                var_name = getattr(var, 'm_name', None)
                if var_name:
                    variables.append(var_name)

            if variables:
                bindings['ValueVariables'] = variables

    return bindings if bindings else None


def extract_uxml_bindings(bundle_path):
    """Extract binding information from a Unity bundle."""
    bundle = UnityPy.load(str(bundle_path))

    results = []

    for obj in bundle.objects:
        if obj.type.name != 'MonoBehaviour':
            continue

        try:
            data = obj.read()
            uxml_name = getattr(data, 'm_Name', '')

            if not uxml_name:
                continue

            # Access the managed references registry
            refs = getattr(data, 'references', None)
            if not refs:
                continue

            ref_ids = getattr(refs, 'RefIds', [])
            if not ref_ids:
                continue

            uxml_bindings = {
                'name': uxml_name,
                'elements': []
            }

            # Process each referenced element
            for ref_obj in ref_ids:
                rid = getattr(ref_obj, 'rid', None)
                ref_type = getattr(ref_obj, 'type', None)
                ref_data = getattr(ref_obj, 'data', None)

                if rid is None or rid == -2 or not ref_data:
                    continue

                # Get type information
                type_class = getattr(ref_type, 'class', '')
                type_ns = getattr(ref_type, 'ns', '')
                full_type = f"{type_ns}.{type_class}" if type_ns else type_class

                # Extract bindings
                bindings = extract_bindings_from_serialized_data(ref_data)

                if bindings:
                    element_name = getattr(ref_data, 'name', '')

                    uxml_bindings['elements'].append({
                        'rid': rid,
                        'type': full_type,
                        'name': element_name,
                        'bindings': bindings
                    })

            if uxml_bindings['elements']:
                results.append(uxml_bindings)

        except Exception as e:
            print(f"Error processing object: {e}")
            continue

    return results


def main():
    # Test with a few interesting bundles
    test_bundles = [
        'bundles/ui-tiles_assets_all.bundle',
        'bundles/ui-screens_assets_common.bundle',
        'bundles/ui-panels_assets_common.bundle'
    ]

    for bundle_path in test_bundles:
        if not Path(bundle_path).exists():
            print(f"Skipping {bundle_path} - not found")
            continue

        print(f"\n{'='*80}")
        print(f"Extracting bindings from: {bundle_path}")
        print('='*80)

        results = extract_uxml_bindings(bundle_path)

        # Show first few results
        for uxml in results[:5]:
            print(f"\n{uxml['name']}")
            print('-' * len(uxml['name']))

            for elem in uxml['elements'][:10]:  # First 10 elements per UXML
                print(f"\n  {elem['type']}")
                if elem['name']:
                    print(f"    name: {elem['name']}")

                for binding_name, binding_value in elem['bindings'].items():
                    if isinstance(binding_value, list):
                        print(f"    {binding_name}:")
                        for item in binding_value:
                            print(f"      - {item}")
                    else:
                        print(f"    {binding_name}: {binding_value}")

        print(f"\nTotal UXML files with bindings: {len(results)}")


if __name__ == '__main__':
    main()
