"""
UXML Exporter - VisualTreeAsset → UXML Text

Exports Unity's VisualTreeAsset objects to human-readable UXML text files.
Handles hierarchy reconstruction, attribute extraction, and inline style serialization.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from .uxml_ast import (
    UXMLDocument,
    UXMLElement,
    UXMLAttribute,
    UXMLTemplate,
)
from .style_parser import StyleParser
from ..logger import get_logger

log = get_logger(__name__)


class UXMLExporter:
    """Exports VisualTreeAsset objects to UXML text."""

    def __init__(self):
        """Initialize the UXML exporter."""
        self.style_parser = StyleParser()
        self._ref_by_id: Dict[int, Any] = {}  # Cache for references lookup

    def export_visual_tree_asset(
        self,
        vta_data: Any,
        output_path: Optional[Path] = None
    ) -> UXMLDocument:
        """
        Export a VisualTreeAsset to a UXML document.

        Args:
            vta_data: Unity VisualTreeAsset object from UnityPy
            output_path: Optional path to write UXML file

        Returns:
            UXMLDocument object
        """
        asset_name = getattr(vta_data, "m_Name", "Unknown")
        log.info(f"Exporting VisualTreeAsset: {asset_name}")

        # Build references lookup for binding extraction
        self._build_references_lookup(vta_data)

        # Create UXML document
        doc = UXMLDocument(asset_name=asset_name)

        # Extract templates
        doc.templates = self._extract_templates(vta_data)

        # Extract stylesheet references
        doc.stylesheets = self._extract_stylesheets(vta_data)

        # Extract visual element hierarchy
        doc.root = self._extract_visual_tree(vta_data)

        # Extract inline styles (from associated StyleSheet)
        inline_stylesheet = self._get_inline_stylesheet(vta_data)
        if inline_stylesheet:
            doc.inline_styles = self.style_parser.parse_stylesheet(inline_stylesheet)

        # Write to file if path provided
        if output_path:
            self.write_uxml(doc, output_path)

        return doc

    def _extract_templates(self, vta_data: Any) -> List[UXMLTemplate]:
        """
        Extract template references from VisualTreeAsset.

        Args:
            vta_data: Unity VisualTreeAsset object

        Returns:
            List of UXMLTemplate objects
        """
        templates = []

        # Unity stores template references in m_TemplateAssets
        template_assets = getattr(vta_data, "m_TemplateAssets", [])

        for template_ref in template_assets:
            # Template reference contains PPtr to another VisualTreeAsset
            # In bundles, this is stored as FileID/PathID
            name = getattr(template_ref, "m_Name", None)
            guid = getattr(template_ref, "guid", None)
            file_id = getattr(template_ref, "m_FileID", None)

            if name:
                templates.append(UXMLTemplate(
                    name=name,
                    src=f"{name}.uxml",  # Conventional path
                    guid=guid,
                    file_id=file_id
                ))

        return templates

    def _extract_stylesheets(self, vta_data: Any) -> List[str]:
        """
        Extract stylesheet references from VisualTreeAsset.

        Args:
            vta_data: Unity VisualTreeAsset object

        Returns:
            List of stylesheet GUIDs/paths
        """
        stylesheets = set()

        # Check all visual elements for stylesheet paths
        visual_elements = getattr(vta_data, "m_VisualElementAssets", [])
        template_elements = getattr(vta_data, "m_TemplateAssets", [])
        all_elements = list(visual_elements) + list(template_elements)

        for elem in all_elements:
            stylesheet_paths = getattr(elem, "m_StylesheetPaths", [])
            for path in stylesheet_paths:
                if path:  # Skip empty strings
                    stylesheets.add(path)

        return list(stylesheets)

    def _extract_visual_tree(self, vta_data: Any) -> Optional[UXMLElement]:
        """
        Extract visual element hierarchy from VisualTreeAsset.

        Args:
            vta_data: Unity VisualTreeAsset object

        Returns:
            Root UXMLElement or None
        """
        # Unity stores visual elements in m_VisualElementAssets
        visual_elements = getattr(vta_data, "m_VisualElementAssets", [])

        # Unity also stores template instances in m_TemplateAssets
        template_elements = getattr(vta_data, "m_TemplateAssets", [])

        # Combine both lists
        all_elements = list(visual_elements) + list(template_elements)

        if not all_elements:
            log.warning("No visual elements found in VisualTreeAsset")
            return None

        # Build element map
        elements_by_id: Dict[int, UXMLElement] = {}

        # First pass: create all elements
        for ve_asset in all_elements:
            element = self._create_element_from_asset(ve_asset, vta_data)
            if element.id is not None:
                elements_by_id[element.id] = element

        # Second pass: build hierarchy using m_Id and m_ParentId
        for ve_asset in all_elements:
            elem_id = getattr(ve_asset, "m_Id", None)
            parent_id = getattr(ve_asset, "m_ParentId", None)

            if elem_id is not None and parent_id is not None and parent_id != 0:
                # This element has a parent (parent_id != 0 means it has a parent)
                if elem_id in elements_by_id and parent_id in elements_by_id:
                    parent = elements_by_id[parent_id]
                    child = elements_by_id[elem_id]
                    parent.children.append(child)

        # Find root element (parent_id == 0)
        root = None
        for ve_asset in all_elements:
            parent_id = getattr(ve_asset, "m_ParentId", None)
            elem_id = getattr(ve_asset, "m_Id", None)

            if parent_id == 0:
                if elem_id is not None and elem_id in elements_by_id:
                    root = elements_by_id[elem_id]
                    break

        # Sort children by orderInDocument
        self._sort_children_recursive(root)

        return root

    def _create_element_from_asset(
        self,
        ve_asset: Any,
        vta_data: Any
    ) -> UXMLElement:
        """
        Create a UXMLElement from a VisualElementAsset.

        Args:
            ve_asset: Unity VisualElementAsset object
            vta_data: Parent VisualTreeAsset (for string lookups)

        Returns:
            UXMLElement object
        """
        # Get element type
        type_name = self._get_element_type_name(ve_asset)

        # Create element
        element = UXMLElement(
            element_type=type_name,
            id=getattr(ve_asset, "m_Id", None),
            parent_id=getattr(ve_asset, "m_ParentId", None),
            order_in_document=getattr(ve_asset, "m_OrderInDocument", None)
        )

        # Extract attributes from UxmlTraits
        attributes = self._extract_attributes(ve_asset, vta_data)
        element.attributes = attributes

        # Extract text content (for Label, Button, etc.)
        element.text = self._extract_text_content(ve_asset, vta_data)

        # Extract template reference if this is a Template instance
        template_ref = getattr(ve_asset, "m_Template", None)
        if template_ref:
            element.template_asset = getattr(template_ref, "m_Name", None)

        return element

    def _get_element_type_name(self, ve_asset: Any) -> str:
        """
        Get the element type name from a VisualElementAsset.

        Args:
            ve_asset: Unity VisualElementAsset object

        Returns:
            Element type name (e.g., "VisualElement", "Label", "Button")
        """
        # Check if this is a template asset (has m_TemplateAlias)
        template_alias = getattr(ve_asset, "m_TemplateAlias", None)
        if template_alias:
            return "TemplateContainer"

        # Unity stores the full type name in m_FullTypeName
        # e.g., "UnityEngine.UIElements.Label" -> "Label"
        # or "SI.Bindable.SIText" -> "SIText"
        full_type = getattr(ve_asset, "m_FullTypeName", None)

        if full_type:
            # Extract the last part after the final dot
            parts = full_type.split('.')
            type_name = parts[-1]

            # Handle special case: UXML root element
            if type_name == "UXML":
                type_name = "VisualElement"

            return type_name

        # Fallback
        return "VisualElement"

    def _extract_attributes(
        self,
        ve_asset: Any,
        vta_data: Any
    ) -> List[UXMLAttribute]:
        """
        Extract UXML attributes from VisualElementAsset.

        Args:
            ve_asset: Unity VisualElementAsset object
            vta_data: Parent VisualTreeAsset

        Returns:
            List of UXMLAttribute objects
        """
        attributes = []

        # Extract name attribute
        name_value = getattr(ve_asset, "m_Name", "")
        if name_value:
            attributes.append(UXMLAttribute(name="name", value=name_value))

        # Extract class list
        classes = getattr(ve_asset, "m_Classes", [])
        if classes:
            # Classes are already strings in Unity 2021+
            attributes.append(UXMLAttribute(
                name="class",
                value=" ".join(classes)
            ))

        # Extract properties (custom attributes)
        properties = getattr(ve_asset, "m_Properties", [])
        for prop in properties:
            prop_name = getattr(prop, "m_Name", None)
            if not prop_name:
                continue

            # Get property value
            # Properties can have different value types
            prop_value = self._extract_property_value(prop)
            if prop_value is not None:
                attributes.append(UXMLAttribute(
                    name=prop_name,
                    value=str(prop_value)
                ))

        # Extract binding attributes
        binding_attrs = self._extract_binding_attributes(ve_asset, vta_data)
        attributes.extend(binding_attrs)

        return attributes

    def _extract_property_value(self, prop: Any) -> Optional[str]:
        """
        Extract property value from a UxmlAttributeDescription.

        Args:
            prop: Property object

        Returns:
            Property value as string or None
        """
        # Try to get the value from various possible fields
        # Unity properties can store values in different ways

        # Check for string value
        str_value = getattr(prop, "m_Value", None)
        if str_value is not None:
            return str(str_value)

        # Check for bool value
        bool_value = getattr(prop, "m_BoolValue", None)
        if bool_value is not None:
            return "true" if bool_value else "false"

        # Check for int value
        int_value = getattr(prop, "m_IntValue", None)
        if int_value is not None:
            return str(int_value)

        # Check for float value
        float_value = getattr(prop, "m_FloatValue", None)
        if float_value is not None:
            return str(float_value)

        return None

    def _extract_text_content(
        self,
        ve_asset: Any,
        vta_data: Any
    ) -> Optional[str]:
        """
        Extract text content from element (for Label, Button, etc.).

        Args:
            ve_asset: Unity VisualElementAsset object
            vta_data: Parent VisualTreeAsset

        Returns:
            Text content or None
        """
        # Check for text field (stored as string in Unity 2021+)
        text_value = getattr(ve_asset, "m_Text", None)
        if text_value and isinstance(text_value, str):
            return text_value

        return None

    def _build_references_lookup(self, vta_data: Any) -> None:
        """
        Build a lookup dictionary mapping element IDs to their binding data.

        Args:
            vta_data: Unity VisualTreeAsset object
        """
        self._ref_by_id = {}

        # Get references from VTA
        references = getattr(vta_data, "references", None)
        if not references:
            return

        ref_ids = getattr(references, "RefIds", [])

        # Build lookup by uxmlAssetId
        for ref_obj in ref_ids:
            ref_data = getattr(ref_obj, "data", None)
            if ref_data:
                uxml_id = getattr(ref_data, "uxmlAssetId", None)
                if uxml_id is not None:
                    self._ref_by_id[uxml_id] = ref_data

    def _extract_binding_attributes(
        self,
        ve_asset: Any,
        vta_data: Any
    ) -> List[UXMLAttribute]:
        """
        Extract binding-related attributes from element's reference data.

        Args:
            ve_asset: Unity VisualElementAsset object
            vta_data: Parent VisualTreeAsset

        Returns:
            List of UXMLAttribute objects for bindings
        """
        attributes = []

        # Get element ID
        elem_id = getattr(ve_asset, "m_Id", None)
        if elem_id is None or elem_id not in self._ref_by_id:
            return attributes

        ref_data = self._ref_by_id[elem_id]

        # Extract TextBinding (for SIText elements)
        text_binding = getattr(ref_data, "TextBinding", None)
        if text_binding:
            path = self._extract_binding_path(text_binding)
            if path:
                attributes.append(UXMLAttribute(
                    name="text-binding",
                    value=path
                ))

        # Extract Binding (for BindableSwitchElement, SIImage, etc.)
        binding = getattr(ref_data, "Binding", None)
        if binding:
            path = self._extract_binding_path(binding)
            if path:
                attributes.append(UXMLAttribute(
                    name="data-binding",
                    value=path
                ))

        # Extract selection bindings (for TabbedGridLayoutElement)
        current_sel_binding = getattr(ref_data, "CurrentSelectedIdBinding", None)
        if current_sel_binding:
            path = self._extract_simple_binding_path(current_sel_binding)
            if path:
                attributes.append(UXMLAttribute(
                    name="current-selected-id-binding",
                    value=path
                ))

        selection_binding = getattr(ref_data, "SelectionBinding", None)
        if selection_binding:
            path = self._extract_simple_binding_path(selection_binding)
            if path:
                attributes.append(UXMLAttribute(
                    name="selection-binding",
                    value=path
                ))

        selected_tab_binding = getattr(ref_data, "SelectedTabBinding", None)
        if selected_tab_binding:
            path = self._extract_simple_binding_path(selected_tab_binding)
            if path:
                attributes.append(UXMLAttribute(
                    name="selected-tab-binding",
                    value=path
                ))

        # Extract mappings (for BindingRemapper)
        mappings = getattr(ref_data, "Mappings", [])
        if mappings and len(mappings) > 0:
            # Serialize mappings as JSON-like format
            mapping_strs = []
            for mapping in mappings:
                from_var = getattr(mapping, 'from_', None)
                to_obj = getattr(mapping, 'to', None)
                to_path = None
                if to_obj:
                    to_path = getattr(to_obj, 'm_path', None)
                if from_var and to_path:
                    mapping_strs.append(f"{from_var}={to_path}")

            if mapping_strs:
                attributes.append(UXMLAttribute(
                    name="binding-mappings",
                    value=";".join(mapping_strs)
                ))

        # Extract template reference (for TemplateContainer elements)
        template_id = getattr(ref_data, "templateId", None)
        if template_id and template_id.strip():
            attributes.append(UXMLAttribute(
                name="template",
                value=template_id
            ))

        return attributes

    def _extract_binding_path(self, binding_obj: Any) -> Optional[str]:
        """
        Extract binding path from a BindingMethod object.

        Args:
            binding_obj: Unity BindingMethod object

        Returns:
            Binding path string or None
        """
        if binding_obj is None:
            return None

        # Get m_kind (1=direct, 2=visual function)
        kind = getattr(binding_obj, 'm_kind', None)

        if kind == 1:  # Direct binding
            direct = getattr(binding_obj, 'm_direct', None)
            if direct:
                path = getattr(direct, 'm_path', None)
                if path and path.strip():
                    return path
        elif kind == 2:  # Visual function binding
            # For visual functions, we can't extract a simple path
            # Return a marker to indicate this is a visual function
            visual_func = getattr(binding_obj, 'm_visualFunction', None)
            if visual_func:
                is_assigned = getattr(visual_func, 'm_isAssigned', 0)
                if is_assigned:
                    return "[VisualFunction]"

        return None

    def _extract_simple_binding_path(self, binding_obj: Any) -> Optional[str]:
        """
        Extract path from a simple BindingPath object.

        Args:
            binding_obj: Unity BindingPath object

        Returns:
            Binding path string or None
        """
        if binding_obj is None:
            return None

        path = getattr(binding_obj, 'm_path', None)
        if path and path.strip():
            return path

        return None

    def _sort_children_recursive(self, element: Optional[UXMLElement]) -> None:
        """
        Sort children by orderInDocument recursively.

        Args:
            element: UXMLElement to process
        """
        if not element:
            return

        # Sort children by orderInDocument
        element.children.sort(key=lambda e: e.order_in_document or 0)

        # Recursively sort grandchildren
        for child in element.children:
            self._sort_children_recursive(child)

    def _get_inline_stylesheet(self, vta_data: Any) -> Optional[Any]:
        """
        Get the inline StyleSheet associated with a VisualTreeAsset.

        Args:
            vta_data: Unity VisualTreeAsset object

        Returns:
            StyleSheet object or None
        """
        # Unity stores inline styles in m_InlineSheet
        inline_sheet = getattr(vta_data, "m_InlineSheet", None)

        if inline_sheet:
            # This might be a PPtr reference or direct object
            # Try to read it
            try:
                if hasattr(inline_sheet, "read"):
                    return inline_sheet.read()
                else:
                    return inline_sheet
            except Exception as e:
                log.warning(f"Failed to read inline stylesheet: {e}")
                return None

        return None

    def write_uxml(self, doc: UXMLDocument, output_path: Path) -> None:
        """
        Write UXML document to file.

        Args:
            doc: UXMLDocument to write
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build XML tree with proper Unity namespaces
        # Register namespaces to avoid ns0: prefixes
        ET.register_namespace("ui", "UnityEngine.UIElements")
        ET.register_namespace("uie", "UnityEditor.UIElements")
        ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

        # Create root element
        root_elem = ET.Element("{UnityEngine.UIElements}UXML")
        root_elem.set("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
                      "../../UIElementsSchema/UIElements.xsd")
        root_elem.set("editor-extension-mode", "False")

        # Add templates
        for template in doc.templates:
            template_elem = ET.SubElement(root_elem, "Template")
            template_elem.set("name", template.name)
            template_elem.set("src", template.src)

        # Add stylesheet references
        for stylesheet in doc.stylesheets:
            style_elem = ET.SubElement(root_elem, "Style")
            # Use GUID as src (Unity's convention)
            style_elem.set("src", f"#{stylesheet}")

        # Add visual tree (skip the root UXML element itself, add its children)
        if doc.root:
            # If root is a VisualElement that was the UXML wrapper, add its children directly
            # Otherwise, add the root element
            if doc.root.element_type == "VisualElement" and not doc.root.attributes:
                # This is the wrapper element, add its children
                for child in doc.root.children:
                    self._build_xml_element(child, root_elem)
            else:
                # Add the root element itself
                self._build_xml_element(doc.root, root_elem)

        # Add inline styles as Style element (if present)
        if doc.inline_styles:
            # Could add as comment or as separate file reference
            style_comment = ET.Comment(f"\n Inline Styles:\n{doc.inline_styles}\n")
            root_elem.append(style_comment)

        # Convert to pretty-printed XML
        xml_str = ET.tostring(root_elem, encoding='unicode')
        try:
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")

            # Remove extra blank lines and the XML declaration
            lines = []
            for line in pretty_xml.split('\n'):
                if line.strip() and not line.strip().startswith('<?xml'):
                    lines.append(line)
            pretty_xml = '\n'.join(lines)

        except Exception as e:
            log.warning(f"Failed to pretty-print XML: {e}")
            pretty_xml = xml_str

        # Write to file
        output_path.write_text(pretty_xml, encoding='utf-8')
        log.info(f"Wrote UXML to {output_path}")

    def _build_xml_element(
        self,
        element: UXMLElement,
        parent_xml: ET.Element
    ) -> None:
        """
        Recursively build XML elements.

        Args:
            element: UXMLElement to convert
            parent_xml: Parent XML element
        """
        # All UI elements use the ui: namespace (UnityEngine.UIElements)
        # This includes both standard Unity elements and custom SI elements
        xml_elem = ET.SubElement(parent_xml, f"{{UnityEngine.UIElements}}{element.element_type}")

        # Add attributes
        for attr in element.attributes:
            xml_elem.set(attr.name, attr.value)

        # Add text content
        if element.text:
            xml_elem.text = element.text

        # Add children recursively
        for child in element.children:
            self._build_xml_element(child, xml_elem)
