"""
UXML Importer - UXML Text → VisualTreeAsset

Imports UXML text files and converts them back into Unity's VisualTreeAsset format.
Handles XML parsing, AST construction, and Unity structure rebuilding.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .uxml_ast import (
    UXMLDocument,
    UXMLElement,
    UXMLAttribute,
    UXMLTemplate,
)
from .style_serializer import StyleSerializer
from ..logger import get_logger

log = get_logger(__name__)


class UXMLImporter:
    """Imports UXML text files into VisualTreeAsset structures."""

    def __init__(self):
        """Initialize the UXML importer."""
        self.style_serializer = StyleSerializer()

    def import_uxml(self, uxml_path: Path) -> UXMLDocument:
        """
        Import UXML from file.

        Args:
            uxml_path: Path to UXML file

        Returns:
            UXMLDocument object
        """
        log.info(f"Importing UXML from {uxml_path}")

        # Parse XML
        tree = ET.parse(str(uxml_path))
        root_xml = tree.getroot()

        # Create document
        doc = UXMLDocument(asset_name=uxml_path.stem)

        # Extract templates
        doc.templates = self._extract_templates_from_xml(root_xml)

        # Extract visual tree
        doc.root = self._extract_visual_tree_from_xml(root_xml)

        # Extract inline styles from comments (if present)
        doc.inline_styles = self._extract_inline_styles_from_xml(root_xml)

        return doc

    def import_uxml_text(
        self, uxml_text: str, asset_name: str = "Imported"
    ) -> UXMLDocument:
        """
        Import UXML from text string.

        Args:
            uxml_text: UXML text content
            asset_name: Name for the asset

        Returns:
            UXMLDocument object
        """
        log.info(f"Importing UXML text for {asset_name}")

        # Parse XML
        root_xml = ET.fromstring(uxml_text)

        # Create document
        doc = UXMLDocument(asset_name=asset_name)

        # Extract templates
        doc.templates = self._extract_templates_from_xml(root_xml)

        # Extract visual tree
        doc.root = self._extract_visual_tree_from_xml(root_xml)

        # Extract inline styles
        doc.inline_styles = self._extract_inline_styles_from_xml(root_xml)

        return doc

    def parse_uxml_to_dict(self, uxml_path: Path) -> Dict[str, Any]:
        """
        Parse UXML file and return Unity VisualTreeAsset structure as dictionary.

        This is used for binary patching approach, not for direct UnityPy serialization.

        Args:
            uxml_path: Path to UXML file

        Returns:
            Dictionary representing VisualTreeAsset with m_VisualElementAssets list
        """
        log.info(f"Parsing UXML to dictionary: {uxml_path}")

        # Parse XML
        tree = ET.parse(str(uxml_path))
        root_xml = tree.getroot()

        # Remove namespace for easier processing
        for elem in root_xml.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}")[1]

        # Build the structure
        visual_elements, template_assets = self._build_element_assets_from_xml(root_xml)

        result = {
            "m_VisualElementAssets": visual_elements,
            "m_TemplateAssets": template_assets,
            "m_UxmlObjectAssets": [],
        }

        return result

    def _build_element_assets_from_xml(
        self, root_xml: ET.Element
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Convert XML elements to m_VisualElementAssets and m_TemplateAssets lists.

        Args:
            root_xml: XML root element

        Returns:
            Tuple of (visual_elements, template_assets)
        """
        visual_elements = []
        template_assets = []
        element_counter = [0]  # Use list for mutable counter in nested function

        def process_element(
            elem: ET.Element, parent_id: int = 0
        ) -> Optional[Dict[str, Any]]:
            """Recursively process XML elements."""

            # Get element ID from data-unity-id attribute (if present in exported UXML)
            # Otherwise use counter
            unity_id_str = elem.get("data-unity-id")
            if unity_id_str:
                try:
                    element_id = int(unity_id_str)
                except ValueError:
                    element_id = element_counter[0]
                    element_counter[0] += 1
            else:
                element_id = element_counter[0]
                element_counter[0] += 1

            # Check if this is a TemplateContainer
            is_template = elem.tag == "TemplateContainer"
            template_alias = elem.get("template") if is_template else None

            # Build the element asset
            element_asset = {
                "m_Id": element_id,
                "m_OrderInDocument": len(visual_elements) + len(template_assets),
                "m_ParentId": parent_id,
                "m_RuleIndex": -1,
                "m_Type": elem.tag,
                "m_Name": elem.get("name", ""),
                "m_Classes": elem.get("class", "").split() if elem.get("class") else [],
            }

            # Capture binding attributes (needed for data connections)
            bindings = {}
            if elem.get("text-binding"):
                bindings["text-binding"] = elem.get("text-binding")
            if elem.get("data-binding"):
                bindings["data-binding"] = elem.get("data-binding")
            if elem.get("current-selected-id-binding"):
                bindings["current-selected-id-binding"] = elem.get(
                    "current-selected-id-binding"
                )
            if elem.get("selection-binding"):
                bindings["selection-binding"] = elem.get("selection-binding")
            if elem.get("selected-tab-binding"):
                bindings["selected-tab-binding"] = elem.get("selected-tab-binding")
            if elem.get("binding-mappings"):
                bindings["binding-mappings"] = elem.get("binding-mappings")

            if bindings:
                element_asset["_bindings"] = bindings

            # Add to appropriate list
            if is_template and template_alias:
                element_asset["m_TemplateAlias"] = template_alias
                template_assets.append(element_asset)
            else:
                visual_elements.append(element_asset)

            # Process children
            for child in elem:
                # Skip Template definitions (they're references, not actual elements)
                if child.tag == "Template":
                    continue
                process_element(child, element_id)

            return element_asset

        # Process all top-level elements
        for child in root_xml:
            # Skip non-element nodes
            if child.tag in ["Template", "Style"] or callable(child.tag):
                continue
            process_element(child)

        return visual_elements, template_assets

    def build_visual_tree_asset(
        self, doc: UXMLDocument, base_vta: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Build Unity VisualTreeAsset data structure from UXML document.

        Args:
            doc: UXMLDocument to convert
            base_vta: Optional existing VTA to use as base

        Returns:
            Dictionary representing Unity VTA structure
        """
        log.info(f"Building VisualTreeAsset for {doc.asset_name}")

        # Initialize data structures
        visual_elements = []
        template_elements = []  # Track template instances separately

        # Convert element tree to Unity format
        element_id = 0

        def process_element(elem: UXMLElement, parent_id: int = -1) -> int:
            nonlocal element_id

            current_id = element_id
            element_id += 1

            # Check if this is a TemplateContainer
            is_template = elem.element_type == "TemplateContainer"
            template_alias = None

            # Build VisualElementAsset structure
            # Unity 2021+ stores data directly (not as string indices)
            ve_asset = {
                "m_Id": current_id,
                "m_ParentId": parent_id,
                "m_OrderInDocument": len(visual_elements) + len(template_elements),
                "m_FullTypeName": self._get_full_type_name(elem.element_type),
                "m_Name": "",
                "m_Classes": [],
            }

            # Process attributes
            for attr in elem.attributes:
                if attr.name == "name":
                    # Unity 2021+ stores name as direct string
                    ve_asset["m_Name"] = attr.value

                elif attr.name == "class":
                    # Unity 2021+ stores classes as direct strings
                    classes = [c.strip() for c in attr.value.split() if c.strip()]
                    ve_asset["m_Classes"] = classes

                elif attr.name == "template":
                    # Template reference - store the template alias
                    template_alias = attr.value

                elif attr.name == "style":
                    # Inline style - store for later processing
                    # Note: Most styles should be in StyleSheet
                    pass

                else:
                    # Other attributes (bindings, etc.) - skip for now
                    # These will need special handling in UxmlSerializedData
                    pass

            # Process text content
            if elem.text:
                # Unity 2021+ stores text as direct string
                ve_asset["m_Text"] = elem.text

            # If this is a template element, add template-specific fields
            if is_template and template_alias:
                ve_asset["m_TemplateAlias"] = template_alias
                template_elements.append(ve_asset)
            else:
                # Regular visual element
                visual_elements.append(ve_asset)

            # Process children
            for child in elem.children:
                process_element(child, current_id)

            return current_id

        # Process the element tree
        if doc.root:
            process_element(doc.root)

        # Build the final VTA structure
        vta_structure = {
            "m_Name": doc.asset_name or "ImportedUXML",
            "m_VisualElementAssets": visual_elements,
            "m_TemplateAssets": template_elements,  # Template instances from UXML
        }

        # If we have inline styles, we need to build a StyleSheet
        if doc.inline_styles:
            inline_stylesheet = self._build_inline_stylesheet(doc.inline_styles)
            vta_structure["m_InlineSheet"] = inline_stylesheet

        return vta_structure

    def _get_full_type_name(self, element_type: str) -> str:
        """
        Convert element type to full Unity type name.

        Args:
            element_type: Short element type (e.g., "Label", "Button")

        Returns:
            Full type name (e.g., "UnityEngine.UIElements.Label")
        """
        # Map of common SI.Bindable types
        si_bindable_types = {
            "BindingRoot",
            "BindingVariables",
            "BindingRemapper",
            "BindableSwitchElement",
            "SIText",
            "SIImage",
            "SIButton",
            "SIVisible",
            "SIDropdown",
            "TabbedGridLayoutElement",
        }

        # Check if it's an SI.Bindable type
        if element_type in si_bindable_types:
            return f"SI.Bindable.{element_type}"

        # Default to UnityEngine.UIElements namespace
        return f"UnityEngine.UIElements.{element_type}"

    def _extract_templates_from_xml(self, root_xml: ET.Element) -> List[UXMLTemplate]:
        """
        Extract template references from XML.

        Args:
            root_xml: Root XML element

        Returns:
            List of UXMLTemplate objects
        """
        templates = []

        for template_elem in root_xml.findall(".//Template"):
            name = template_elem.get("name", "")
            src = template_elem.get("src", "")

            if name:
                templates.append(UXMLTemplate(name=name, src=src))

        return templates

    def _extract_visual_tree_from_xml(
        self, root_xml: ET.Element
    ) -> Optional[UXMLElement]:
        """
        Extract visual element hierarchy from XML.

        Args:
            root_xml: Root XML element

        Returns:
            Root UXMLElement or None
        """
        # Find all top-level UI elements (skip Template elements)
        top_level_elements = []

        for child in root_xml:
            tag = child.tag

            # Remove namespace prefix
            if "}" in tag:
                tag = tag.split("}")[1]

            # Skip Template, Style elements and comments
            if tag in ("Template", "Style") or callable(tag):
                continue

            # This is a UI element
            top_level_elements.append(self._parse_xml_element(child))

        # If there's only one top-level element, return it
        if len(top_level_elements) == 1:
            return top_level_elements[0]

        # If there are multiple top-level elements, wrap them in a VisualElement
        if len(top_level_elements) > 1:
            wrapper = UXMLElement(element_type="VisualElement")
            wrapper.children = top_level_elements
            return wrapper

        return None

    def _parse_xml_element(self, xml_elem: ET.Element) -> UXMLElement:
        """
        Parse an XML element into a UXMLElement.

        Args:
            xml_elem: XML element to parse

        Returns:
            UXMLElement object
        """
        # Get element type from tag name
        tag = xml_elem.tag

        # Remove namespace prefix
        if "}" in tag:
            tag = tag.split("}")[1]

        element_type = tag

        # Create UXML element
        element = UXMLElement(element_type=element_type)

        # Extract attributes
        for attr_name, attr_value in xml_elem.attrib.items():
            # Remove namespace prefix from attribute name
            if "}" in attr_name:
                attr_name = attr_name.split("}")[1]

            element.attributes.append(UXMLAttribute(name=attr_name, value=attr_value))

        # Extract text content
        if xml_elem.text and xml_elem.text.strip():
            element.text = xml_elem.text.strip()

        # Parse children
        for child_xml in xml_elem:
            child_element = self._parse_xml_element(child_xml)
            element.children.append(child_element)

        return element

    def _extract_inline_styles_from_xml(self, root_xml: ET.Element) -> Optional[str]:
        """
        Extract inline styles from XML comments.

        Args:
            root_xml: Root XML element

        Returns:
            CSS text or None
        """
        # Check for CSS in comments
        # Comments are detected by checking if the tag is a callable (function)
        for elem in root_xml.iter():
            if callable(elem.tag):
                # This is a comment
                comment_text = elem.text or ""
                if "Inline Styles:" in comment_text:
                    # Extract CSS from comment
                    lines = comment_text.split("\n")
                    css_lines = []
                    in_css = False

                    for line in lines:
                        if "Inline Styles:" in line:
                            in_css = True
                            continue

                        if in_css:
                            css_lines.append(line)

                    return "\n".join(css_lines).strip()

        return None

    def _build_inline_stylesheet(self, css_text: str) -> Dict[str, Any]:
        """
        Build Unity StyleSheet structure from CSS text.

        Args:
            css_text: CSS text

        Returns:
            Dictionary representing Unity StyleSheet structure
        """
        # Parse CSS into rules
        rules = self.style_serializer.parse_css(css_text)

        # Build StyleSheet data structures
        strings, colors, unity_rules, complex_selectors = (
            self.style_serializer.build_stylesheet_data(rules)
        )

        # Build StyleSheet structure
        stylesheet = {
            "strings": strings,
            "colors": colors,
            "m_Rules": unity_rules,
            "m_ComplexSelectors": complex_selectors,
        }

        return stylesheet

    def inject_into_bundle(
        self, doc: UXMLDocument, bundle_path: Path, output_path: Path
    ) -> None:
        """
        Inject modified VisualTreeAsset into a Unity bundle.

        Args:
            doc: UXMLDocument to inject
            bundle_path: Path to source bundle
            output_path: Path to write modified bundle
        """
        import UnityPy

        log.info(f"Injecting UXML into bundle: {bundle_path}")

        # Load bundle
        env = UnityPy.load(str(bundle_path))

        # Find the target VisualTreeAsset
        target_vta = None
        target_obj = None

        for obj in env.objects:
            if obj.type.name == "MonoBehaviour":
                # Check if this is a VisualTreeAsset
                # (Unity UI Toolkit uses MonoBehaviour for VTA)
                try:
                    data = obj.read()
                    name = getattr(data, "m_Name", None)

                    if name == doc.asset_name:
                        target_vta = data
                        target_obj = obj
                        break

                    # Also check for VisualTreeAsset type
                    if hasattr(data, "m_VisualElementAssets"):
                        if name == doc.asset_name:
                            target_vta = data
                            target_obj = obj
                            break

                except Exception:
                    continue

        if not target_vta or not target_obj:
            log.error(f"Could not find VisualTreeAsset '{doc.asset_name}' in bundle")
            raise ValueError(f"VisualTreeAsset '{doc.asset_name}' not found")

        # Build new VTA structure
        new_vta_data = self.build_visual_tree_asset(doc, target_vta)

        # Update the VTA object
        # Note: This requires careful field-by-field update
        # Unity's internal structure must be preserved

        for key, value in new_vta_data.items():
            if hasattr(target_vta, key):
                setattr(target_vta, key, value)

        # Save the modified object
        target_obj.save_typetree(target_vta)

        # Write modified bundle
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(env.file.save())

        log.info(f"Wrote modified bundle to {output_path}")
