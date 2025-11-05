"""
UXML Importer - Parse modified UXML files back to Unity structures.

This module handles the round-trip import of UXML files:
1. Parse XML from file
2. Reconstruct VisualTreeAsset structure
3. Rebuild binding data from attributes
4. Validate element IDs and bindings
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class ValidationError:
    """Represents a validation error during import."""
    element_id: Optional[int]
    message: str
    severity: str = "error"  # error, warning, info


class UXMLImporter:
    """Import UXML XML files back to Unity VisualTreeAsset structures."""

    def __init__(self):
        self.errors: List[ValidationError] = []
        # old_id -> new_id if regenerated
        self.element_id_map: Dict[int, int] = {}

    def parse_uxml_file(self, xml_path: str) -> Dict[str, Any]:
        """
        Parse UXML XML file and return Unity VisualTreeAsset structure.

        Args:
            xml_path: Path to the UXML file

        Returns:
            Dictionary representing VisualTreeAsset with:
            - m_VisualElementAssets: List of element definitions
            - m_UxmlObjectAssets: Additional object assets
            - managedReferencesRegistry: Binding data
        """
        self.errors = []
        self.element_id_map = {}

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Remove namespace for easier processing
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}')[1]

            # Build the structure
            visual_elements = self._build_element_assets(root)
            bindings = self._build_managed_references(root, visual_elements)

            result = {
                'm_VisualElementAssets': visual_elements,
                'm_UxmlObjectAssets': [],
                'managedReferencesRegistry': bindings
            }

            # Validate the structure
            self._validate_structure(result)

            return result

        except ET.ParseError as e:
            self.errors.append(ValidationError(
                None, f"XML parse error: {e}", "error"))
            raise
        except Exception as e:
            self.errors.append(ValidationError(
                None, f"Import error: {e}", "error"))
            raise

    def _build_element_assets(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Convert XML elements to m_VisualElementAssets list.

        Args:
            root: XML root element

        Returns:
            List of VisualElementAsset dictionaries
        """
        elements = []
        # Use list for mutable counter in nested function
        element_counter = [0]

        def process_element(elem: ET.Element, parent_id: int = 0) -> Optional[Dict[str, Any]]:
            """Recursively process XML elements."""

            # Get element ID from data-unity-id attribute
            unity_id_str = elem.get('data-unity-id')
            if not unity_id_str:
                self.errors.append(ValidationError(
                    None,
                    f"Element {elem.tag} missing data-unity-id attribute",
                    "warning"
                ))
                return None

            try:
                element_id = int(unity_id_str)
            except ValueError:
                self.errors.append(ValidationError(
                    None,
                    f"Invalid data-unity-id value: {unity_id_str}",
                    "error"
                ))
                return None

            # Build the element asset
            element_asset = {
                'm_Id': element_id,
                'm_OrderInDocument': element_counter[0],
                'm_ParentId': parent_id,
                'm_RuleIndex': -1,
                'm_Type': elem.tag,
                'm_Name': elem.get('name', ''),
                'm_Classes': elem.get('class', '').split() if elem.get('class') else []
            }

            element_counter[0] += 1
            elements.append(element_asset)

            # Process children
            for child in elem:
                # Skip Template includes for now (they're references, not actual elements)
                if child.tag == 'Template':
                    continue
                process_element(child, element_id)

            return element_asset

        # Process all top-level elements
        for child in root:
            process_element(child)

        return elements

    def _build_managed_references(self, root: ET.Element, elements: List[Dict]) -> Dict[str, Any]:
        """
        Rebuild binding data from unity:binding-* attributes.

        Args:
            root: XML root element
            elements: List of element assets

        Returns:
            ManagedReferencesRegistry dictionary
        """
        references = []
        rid_counter = 1000  # Start from 1000 like Unity does

        def extract_bindings(elem: ET.Element) -> Optional[Dict[str, Any]]:
            """Extract binding data from element attributes."""

            # Check if element has binding RID
            binding_rid = elem.get('data-binding-rid')
            if not binding_rid:
                return None

            element_id = int(elem.get('data-unity-id', '0'))

            # Build binding data from attributes
            binding_data = {
                'type': {'class': '', 'ns': '', 'asm': 'Assembly-CSharp'},
                'data': {
                    'uxmlAssetId': element_id
                }
            }

            # Parse specific binding attributes
            for attr_name, attr_value in elem.attrib.items():
                if not attr_name.startswith('data-binding-'):
                    continue

                # Skip the RID itself
                if attr_name == 'data-binding-rid':
                    continue

                # Convert attribute name to property name
                # data-binding-textbinding -> TextBinding
                # data-binding-mappings -> Mappings
                prop_name = attr_name.replace('data-binding-', '')
                prop_name = self._to_pascal_case(prop_name)

                # Parse the value based on property type
                if prop_name == 'Mappings':
                    binding_data['data'][prop_name] = self._parse_mappings(
                        attr_value)
                elif prop_name in ['Parameters', 'ValueVariables']:
                    binding_data['data'][prop_name] = [v.strip()
                                                       for v in attr_value.split(';') if v.strip()]
                else:
                    # Direct binding path
                    binding_data['data'][prop_name] = attr_value

            # Infer binding type from properties
            binding_type = self._infer_binding_type(binding_data['data'])
            binding_data['type']['class'] = binding_type

            return binding_data

        def process_element_bindings(elem: ET.Element):
            """Recursively process bindings for element and children."""
            binding = extract_bindings(elem)
            if binding:
                references.append(binding)

            for child in elem:
                process_element_bindings(child)

        # Process all elements
        for child in root:
            process_element_bindings(child)

        return {
            'version': 2,
            'RefIds': list(range(len(references))),
            'references': references
        }

    def _to_pascal_case(self, snake_or_kebab: str) -> str:
        """Convert snake_case or kebab-case to PascalCase."""
        words = re.split(r'[-_]', snake_or_kebab)
        return ''.join(word.capitalize() for word in words)

    def _parse_mappings(self, mappings_str: str) -> List[Dict[str, Any]]:
        """
        Parse mapping string to list of mapping objects.

        Example: "person -> binding;player -> binding"
        Returns: [
            {'from': 'person', 'to': {'m_path': 'binding'}},
            {'from': 'player', 'to': {'m_path': 'binding'}}
        ]
        """
        mappings = []
        for mapping in mappings_str.split(';'):
            if '->' not in mapping:
                continue

            # Handle HTML-escaped arrows
            mapping = mapping.replace('&gt;', '>')

            from_val, to_val = mapping.split('->', 1)
            mappings.append({
                'from': from_val.strip(),
                'to': {'m_path': to_val.strip()}
            })

        return mappings

    def _infer_binding_type(self, binding_data: Dict[str, Any]) -> str:
        """
        Infer the Unity binding type from the binding data properties.

        Args:
            binding_data: The binding data dictionary

        Returns:
            The inferred binding type class name
        """
        # Map property combinations to binding types
        if 'Mappings' in binding_data:
            return 'SI.Bindable.BindingRemapper'
        elif 'Parameters' in binding_data:
            return 'SI.Bindable.BindingExpect'
        elif 'ValueVariables' in binding_data:
            return 'SI.Bindable.BindingVariables'
        elif 'HoverBinding' in binding_data:
            return 'SI.Bindable.SIButton'
        elif 'TextBinding' in binding_data:
            return 'SI.Bindable.SIText'
        elif 'Binding' in binding_data:
            # Generic binding - try to infer from element type
            return 'SI.Bindable.BindableSwitchElement'

        return 'UnityEngine.UIElements.UxmlSerializedData'

    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """
        Validate the reconstructed VisualTreeAsset structure.

        Args:
            data: The VisualTreeAsset dictionary

        Returns:
            True if valid, False otherwise
        """
        elements = data.get('m_VisualElementAssets', [])
        bindings = data.get('managedReferencesRegistry',
                            {}).get('references', [])

        # Check for duplicate element IDs
        element_ids = [e['m_Id'] for e in elements]
        duplicates = [id for id in element_ids if element_ids.count(id) > 1]
        if duplicates:
            self.errors.append(ValidationError(
                None,
                f"Duplicate element IDs found: {set(duplicates)}",
                "error"
            ))

        # Check all binding uxmlAssetIds reference valid elements
        element_id_set = set(element_ids)
        for i, binding in enumerate(bindings):
            binding_data = binding.get('data', {})
            uxmlAssetId = binding_data.get('uxmlAssetId')

            if uxmlAssetId and uxmlAssetId not in element_id_set:
                self.errors.append(ValidationError(
                    uxmlAssetId,
                    f"Binding {i} references non-existent element ID {uxmlAssetId}",
                    "error"
                ))

        return len([e for e in self.errors if e.severity == "error"]) == 0

    def get_validation_report(self) -> str:
        """
        Get a formatted report of validation errors and warnings.

        Returns:
            Formatted string with all validation messages
        """
        if not self.errors:
            return "✅ No validation errors"

        report = []
        errors = [e for e in self.errors if e.severity == "error"]
        warnings = [e for e in self.errors if e.severity == "warning"]

        if errors:
            report.append(f"❌ {len(errors)} Error(s):")
            for err in errors:
                elem_info = f" [Element {err.element_id}]" if err.element_id else ""
                report.append(f"  - {err.message}{elem_info}")

        if warnings:
            report.append(f"⚠️  {len(warnings)} Warning(s):")
            for warn in warnings:
                elem_info = f" [Element {warn.element_id}]" if warn.element_id else ""
                report.append(f"  - {warn.message}{elem_info}")

        return "\n".join(report)
