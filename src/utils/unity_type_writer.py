"""
Unity Type Writer - Convert Python dictionaries to proper UnityPy types.

This module handles the conversion of parsed UXML data back into
Unity's type system for writing to bundles.
"""

from typing import Any, Dict, List
import UnityPy
from collections import OrderedDict


class UnityTypeWriter:
    """Convert Python data structures to Unity types for bundle writing."""

    def __init__(self, template_obj):
        """
        Initialize with a template object to understand the type structure.

        Args:
            template_obj: An existing Unity object to use as a type template
        """
        self.template_obj = template_obj

    def create_visual_element_asset(self, elem_dict: Dict[str, Any], template_elem: Any = None) -> Any:
        """
        Create a VisualElementAsset from a dictionary.

        Args:
            elem_dict: Dictionary with element properties
            template_elem: Template element to clone type from

        Returns:
            Unity VisualElementAsset object
        """
        if template_elem is None:
            # Get a template element to understand the structure
            if hasattr(self.template_obj, 'm_VisualElementAssets') and len(self.template_obj.m_VisualElementAssets) > 0:
                template_elem = self.template_obj.m_VisualElementAssets[0]

        if template_elem is None:
            # Fallback to OrderedDict if no template available
            elem_type = OrderedDict
            new_elem = elem_type()
        else:
            # Clone the template to preserve __node__ and type information
            elem_type = type(template_elem)
            new_elem = elem_type()

            # Copy __node__ if it exists (critical for UnityPy's type system)
            if hasattr(template_elem, '__node__'):
                new_elem.__node__ = template_elem.__node__

        # Copy all properties from dict to Unity object
        for key, value in elem_dict.items():
            if hasattr(new_elem, key):
                setattr(new_elem, key, value)
            elif isinstance(new_elem, (dict, OrderedDict)):
                new_elem[key] = value

        return new_elem

    def create_managed_reference(self, ref_dict: Dict[str, Any]) -> Any:
        """
        Create a managed reference (binding) object from a dictionary.

        Args:
            ref_dict: Dictionary with reference type and data

        Returns:
            Unity managed reference object
        """
        # Managed references are typically stored as OrderedDicts in UnityPy
        ref = OrderedDict()

        # Copy type information
        if 'type' in ref_dict:
            ref['type'] = OrderedDict(ref_dict['type'])

        # Copy data
        if 'data' in ref_dict:
            ref['data'] = self._convert_binding_data(ref_dict['data'])

        return ref

    def _convert_binding_data(self, data_dict: Dict[str, Any]) -> OrderedDict:
        """
        Convert binding data dictionary to Unity format.

        Args:
            data_dict: Dictionary with binding data

        Returns:
            OrderedDict with Unity-formatted binding data
        """
        result = OrderedDict()

        for key, value in data_dict.items():
            if isinstance(value, list):
                # Convert list of dicts to list of OrderedDicts
                if value and isinstance(value[0], dict):
                    result[key] = [OrderedDict(item) for item in value]
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = OrderedDict(value)
            else:
                result[key] = value

        return result

    def update_visual_tree_asset(self, target_obj: Any, uxml_data: Dict[str, Any]) -> Any:
        """
        Update a VisualTreeAsset with new UXML data.

        Args:
            target_obj: The existing Unity VisualTreeAsset object
            uxml_data: Dictionary with new UXML data

        Returns:
            Updated Unity object
        """
        # Update visual element assets
        if 'm_VisualElementAssets' in uxml_data:
            new_elem_dicts = uxml_data['m_VisualElementAssets']
            existing_elements = list(
                target_obj.m_VisualElementAssets)  # Make a copy

            # Strategy: ONLY update fields that exist in the import data
            # Leave all other Unity fields intact to preserve type information

            # Match elements by ID and update their properties
            try:
                elem_by_id = {getattr(e, 'm_Id', None)
                                      : e for e in existing_elements}
            except Exception as e:
                print(f"DEBUG: Error creating elem_by_id: {e}")
                print(
                    f"DEBUG: First element type: {type(existing_elements[0]) if existing_elements else 'empty'}")
                raise

            for i, elem_dict in enumerate(new_elem_dicts):
                try:
                    elem_id = elem_dict.get('m_Id')

                    if elem_id in elem_by_id:
                        # Update existing element
                        elem = elem_by_id[elem_id]

                        # Only update fields that are in the import dict
                        for key, value in elem_dict.items():
                            if hasattr(elem, key):
                                setattr(elem, key, value)
                    else:
                        # Element doesn't exist - this means the UXML was modified
                        # We need to create a new element, but this is complex
                        # For now, skip new elements
                        pass
                except Exception as e:
                    print(f"DEBUG: Error processing element {i}: {e}")
                    print(f"DEBUG: elem_dict type: {type(elem_dict)}")
                    print(
                        f"DEBUG: elem_dict keys: {list(elem_dict.keys())[:5]}")
                    raise

        # Update UXML object assets
        if 'm_UxmlObjectAssets' in uxml_data:
            target_obj.m_UxmlObjectAssets = uxml_data['m_UxmlObjectAssets']

        # Update managed references (bindings)
        if 'managedReferencesRegistry' in uxml_data:
            registry_data = uxml_data['managedReferencesRegistry']

            # Get or create the registry
            if not hasattr(target_obj, 'managedReferencesRegistry') or target_obj.managedReferencesRegistry is None:
                target_obj.managedReferencesRegistry = OrderedDict()

            registry = target_obj.managedReferencesRegistry

            # Debug: check type
            print(f"DEBUG: registry type = {type(registry)}")
            print(f"DEBUG: registry hasdict = {hasattr(registry, '__dict__')}")

            # Handle different registry types (dict-like or object)
            if hasattr(registry, '__dict__'):
                # It's an object, use attributes
                if 'version' in registry_data:
                    registry.version = registry_data['version']

                if 'RefIds' in registry_data:
                    registry.RefIds = registry_data['RefIds']

                if 'references' in registry_data:
                    new_refs = []
                    for i, ref_dict in enumerate(registry_data['references']):
                        try:
                            new_ref = self.create_managed_reference(ref_dict)
                            new_refs.append(new_ref)
                        except Exception as e:
                            print(f"DEBUG: Error creating reference {i}: {e}")
                            print(f"DEBUG: ref_dict type: {type(ref_dict)}")
                            raise
                    registry.references = new_refs
            else:
                # It's dict-like
                if 'version' in registry_data:
                    registry['version'] = registry_data['version']

                if 'RefIds' in registry_data:
                    registry['RefIds'] = registry_data['RefIds']

                if 'references' in registry_data:
                    new_refs = []
                    for ref_dict in registry_data['references']:
                        new_ref = self.create_managed_reference(ref_dict)
                        new_refs.append(new_ref)
                    registry['references'] = new_refs

        return target_obj


def update_uxml_in_bundle(bundle_obj, asset_name: str, uxml_data: Dict[str, Any]) -> bool:
    """
    Update a UXML asset in a bundle with proper type conversion.

    Args:
        bundle_obj: UnityPy Bundle/ObjectReader
        asset_name: Name of the asset to update
        uxml_data: Dictionary with new UXML data

    Returns:
        True if successful, False otherwise
    """
    try:
        data = bundle_obj.read()

        # Create type writer with template
        writer = UnityTypeWriter(data)

        # Update the object
        updated_obj = writer.update_visual_tree_asset(data, uxml_data)

        # Save back
        bundle_obj.save_typetree(updated_obj)

        return True

    except Exception as e:
        print(f"Failed to update UXML: {e}")
        return False
