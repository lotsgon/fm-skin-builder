"""Utilities for handling UXML data from Unity bundles."""

from __future__ import annotations
from pathlib import Path
import re
from collections import namedtuple
from typing import List, Dict, Set, Any, Optional

StringHit = namedtuple("StringHit", ["offset", "text"])

UI_KEYWORDS = [
    "VisualElement",
    "Label",
    "ScrollView",
    "ListView",
    "Button",
    "Toggle",
    "Calendar",
    "CalendarTool",
    "TextField",
    "DropdownField",
    "Foldout",
    "Box",
    "IMGUIContainer",
    "Template",
    "Element",
]


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

    # Check all attributes for binding data
    for attr in dir(ref_data):
        if attr.startswith('_'):
            continue

        val = getattr(ref_data, attr, None)

        # Look for binding attributes (case-insensitive)
        if 'binding' in attr.lower():
            path = extract_binding_path(val)
            if path:
                bindings[attr] = path

        # Special handling for BindingRemapper Mappings
        if attr == 'Mappings' and val:
            mappings = []
            for mapping in val[:50]:  # First 50 mappings
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
            for param in val[:50]:  # First 50 parameters
                param_name = getattr(param, 'name', None)
                if param_name:
                    params.append(param_name)

            if params:
                bindings['Parameters'] = params

        # Special handling for BindingVariables
        if attr == 'ValueVariables' and val:
            variables = []
            for var in val[:50]:
                var_name = getattr(var, 'm_name', None)
                if var_name:
                    variables.append(var_name)

            if variables:
                bindings['ValueVariables'] = variables

    return bindings if bindings else None


def extract_strings_with_offsets(filename: Path) -> List[StringHit]:
    """Extract strings with offsets from a binary file."""
    hits = []
    with open(filename, "rb") as f:
        data = f.read()
    pattern = re.compile(rb"[ -~]{3,}")
    for match in pattern.finditer(data):
        offset = match.start()
        text = match.group().decode("utf-8", errors="ignore")
        hits.append(StringHit(offset, text))
    return hits


def build_uxml_tree(hits: List[StringHit]) -> str:
    """Build a UXML-like tree from string hits."""
    xml_lines = ["<UXML>"]
    indent = 1
    last_offset = 0
    open_elements = []

    for hit in hits:
        text = hit.text.strip()
        if not text or len(text) > 200:
            continue

        if any(k in text for k in UI_KEYWORDS):
            # Guess indent based on offset difference
            if hit.offset - last_offset > 300:
                indent = max(1, indent - 1)
            elif hit.offset - last_offset < 120:
                indent = min(indent + 1, 6)
            xml_lines.append(
                "  " * indent + f'<Element name="{text}" offset="{hit.offset}">')
            open_elements.append(indent)
        else:
            classes, style = detect_class_or_style(text)
            if classes or style:
                attr_line = []
                if classes:
                    attr_line.append(f'class="{" ".join(classes)}"')
                if style:
                    attr_line.append(f'style="{style}"')
                xml_lines.append("  " * (indent + 1) +
                                 f"<Style {' '.join(attr_line)} />")
            elif text.lower().startswith("uxmlserializeddata"):
                xml_lines.append("  " * (indent + 1) +
                                 "<!-- SerializedData marker -->")
            elif len(text) < 60:
                xml_lines.append("  " * (indent + 1) +
                                 f"<!-- attr: {text} -->")

        last_offset = hit.offset

    # Close elements
    for _ in range(len(open_elements)):
        indent = open_elements.pop()
        xml_lines.append("  " * indent + "</Element>")
    xml_lines.append("</UXML>")
    return "\n".join(xml_lines)


def detect_class_or_style(text: str) -> tuple:
    """Detect classes or inline styles in text."""
    classes, style = [], None
    if re.match(r"^[.#]?[A-Za-Z0-9_\-]+$", text) or "class" in text.lower():
        if text.startswith("."):
            classes.append(text.strip())
        elif "class" in text.lower():
            parts = re.findall(r"[A-Za-Z0-9_\-]+", text)
            classes.extend(parts[1:]) if len(parts) > 1 else classes
    if ":" in text and ";" in text:
        style = text.strip()
    return classes, style


class UXMLDocument:
    """Represents a parsed UXML document from Unity's VisualTreeAsset structure."""

    def __init__(self, name: str, bundle: str):
        self.name = name
        self.bundle = bundle
        self.elements: List[Dict[str, Any]] = []
        self.classes_used: Set[str] = set()
        self.stylesheets: List[str] = []
        self.has_inline_styles = False
        self.element_types: Set[str] = set()
        # Track component types (fully qualified names)
        self.component_types: Set[str] = set()
        self.custom_component_types: Set[str] = set()  # SI.*, FM.* components
        # NEW: Track template references (UXML composition)
        self.templates_used: List[str] = []  # List of m_TemplateAlias values
        self.template_details: List[Dict[str, Any]] = []  # Full template info
        # NEW: Track data bindings (connects UI to game data)
        # List of binding info per element
        self.bindings: List[Dict[str, Any]] = []

    def add_element(self, element_data: Any):
        """Add a VisualElementAsset to the document."""
        elem_info = {}

        # Extract element name
        if hasattr(element_data, 'm_Name'):
            name = getattr(element_data, 'm_Name', '')
            if name:
                elem_info['name'] = name

        # Extract type
        if hasattr(element_data, 'm_FullTypeName'):
            type_name = getattr(element_data, 'm_FullTypeName', '')
            if type_name:
                elem_info['type'] = type_name
                # Track full component type
                self.component_types.add(type_name)

                # Identify custom components (SI.*, FM.*, etc.)
                if type_name.startswith('SI.') or type_name.startswith('FM.'):
                    self.custom_component_types.add(type_name)

                # Extract just the class name (e.g., "UnityEngine.UIElements.Button" -> "Button")
                if '.' in type_name:
                    short_type = type_name.split('.')[-1]
                    self.element_types.add(short_type)
                else:
                    self.element_types.add(type_name)

        # Extract classes
        if hasattr(element_data, 'm_Classes'):
            classes = getattr(element_data, 'm_Classes', [])
            if classes:
                # Normalize to .class format
                normalized = [cls if cls.startswith(
                    '.') else f'.{cls}' for cls in classes]
                elem_info['classes'] = normalized
                self.classes_used.update(normalized)

        # Extract text content
        if hasattr(element_data, 'm_Text'):
            text = getattr(element_data, 'm_Text', '')
            if text:
                elem_info['text'] = text

        # Check for inline styles in properties
        if hasattr(element_data, 'm_Properties'):
            props = getattr(element_data, 'm_Properties', [])
            if props and len(props) > 0:
                self.has_inline_styles = True
                elem_info['has_inline_styles'] = True

        # Extract stylesheet paths at element level
        if hasattr(element_data, 'm_StylesheetPaths'):
            paths = getattr(element_data, 'm_StylesheetPaths', [])
            if paths:
                elem_info['stylesheet_paths'] = paths
                self.stylesheets.extend(paths)

        # Add element if it has meaningful data
        if elem_info:
            self.elements.append(elem_info)

    def to_dict(self) -> Dict[str, Any]:
        """Export document as dictionary for catalog."""
        return {
            'bundle': self.bundle,
            'stylesheets': list(set(self.stylesheets)),  # Deduplicate
            'has_inline_styles': self.has_inline_styles,
            'classes_used': sorted(list(self.classes_used)),
            'variables_used': [],  # Will be populated by catalog builder
            'elements': sorted(list(self.element_types)),
            'element_count': len(self.elements),
            # Component type tracking
            'component_types': sorted(list(self.component_types)),
            'custom_components': sorted(list(self.custom_component_types)),
            # NEW: Template tracking
            'templates_used': sorted(list(set(self.templates_used))),
            'template_count': len(self.templates_used),
            'template_details': self.template_details,
            # NEW: Data binding tracking
            'bindings': self.bindings,
            'binding_count': len(self.bindings)
        }


def parse_visual_tree_asset(data: Any, name: str, bundle: str) -> Optional[UXMLDocument]:
    """Parse a Unity VisualTreeAsset (MonoBehaviour with m_VisualElementAssets).

    Args:
        data: The MonoBehaviour data object
        name: Name of the asset
        bundle: Bundle name where this asset was found

    Returns:
        UXMLDocument if this is a valid VisualTreeAsset, None otherwise
    """
    # Check if this has VisualElementAssets (main UXML structure)
    if not hasattr(data, 'm_VisualElementAssets'):
        return None

    elements = getattr(data, 'm_VisualElementAssets', [])
    if not elements:
        return None

    # Create document
    doc = UXMLDocument(name, bundle)

    # Parse parent-level stylesheets
    if hasattr(data, 'm_Stylesheets'):
        parent_stylesheets = getattr(data, 'm_Stylesheets', [])
        if parent_stylesheets:
            # These might be PPtr references, extract names if possible
            for ss in parent_stylesheets:
                if hasattr(ss, 'm_Name'):
                    ss_name = getattr(ss, 'm_Name', '')
                    if ss_name:
                        doc.stylesheets.append(ss_name)

    if hasattr(data, 'm_StylesheetPaths'):
        paths = getattr(data, 'm_StylesheetPaths', [])
        doc.stylesheets.extend(paths)

    # NEW: Parse template assets (UXML composition/includes)
    if hasattr(data, 'm_TemplateAssets'):
        template_assets = getattr(data, 'm_TemplateAssets', [])
        for tmpl in template_assets:
            # Extract template alias (the name of the included UXML file)
            template_alias = getattr(tmpl, 'm_TemplateAlias', '')
            if template_alias:
                doc.templates_used.append(template_alias)

                # Store detailed template info
                template_info = {
                    'alias': template_alias,
                    'id': getattr(tmpl, 'm_Id', None),
                    'parent_id': getattr(tmpl, 'm_ParentId', None),
                    'classes': getattr(tmpl, 'm_Classes', []),
                    'order': getattr(tmpl, 'm_OrderInDocument', -1)
                }
                doc.template_details.append(template_info)

    # Parse all visual elements
    for element in elements:
        doc.add_element(element)

    # NEW: Parse managed references (data bindings)
    if hasattr(data, 'references'):
        refs = getattr(data, 'references', None)
        if refs and hasattr(refs, 'RefIds'):
            ref_ids = getattr(refs, 'RefIds', [])

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

                    doc.bindings.append({
                        'rid': rid,
                        'type': full_type,
                        'name': element_name,
                        'bindings': bindings
                    })

    return doc


def visual_tree_asset_to_xml(data: Any, name: str) -> str:
    """Convert VisualTreeAsset to human-readable XML/UXML format.

    Args:
        data: The MonoBehaviour data with m_VisualElementAssets
        name: Name of the asset

    Returns:
        Formatted XML string representing the UXML structure
    """
    if not hasattr(data, 'm_VisualElementAssets'):
        return f"<!-- Not a VisualTreeAsset: {name} -->"

    elements = getattr(data, 'm_VisualElementAssets', [])
    if not elements:
        return f"<!-- Empty VisualTreeAsset: {name} -->"

    xml_lines = ['<ui:UXML xmlns:ui="UnityEngine.UIElements">']

    # Add stylesheet references
    stylesheets = []
    if hasattr(data, 'm_StylesheetPaths'):
        stylesheets.extend(getattr(data, 'm_StylesheetPaths', []))

    for stylesheet in stylesheets:
        xml_lines.append(f'    <Style src="{stylesheet}" />')

    if stylesheets:
        xml_lines.append('')  # Blank line after stylesheets

    # NEW: Add template references as comments
    if hasattr(data, 'm_TemplateAssets'):
        template_assets = getattr(data, 'm_TemplateAssets', [])
        if template_assets:
            xml_lines.append('    <!-- UXML Templates Used In This File -->')
            for tmpl in template_assets:
                template_alias = getattr(tmpl, 'm_TemplateAlias', '')
                if template_alias:
                    tmpl_classes = getattr(tmpl, 'm_Classes', [])
                    class_str = f' class="{" ".join(tmpl_classes)}"' if tmpl_classes else ''
                    xml_lines.append(
                        f'    <!-- Template: {template_alias}{class_str} -->')
            xml_lines.append('')

    # NEW: Add binding information as structured comments
    if hasattr(data, 'references'):
        refs = getattr(data, 'references', None)
        if refs and hasattr(refs, 'RefIds'):
            ref_ids = getattr(refs, 'RefIds', [])

            # Collect bindings
            binding_list = []
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
                    binding_list.append({
                        'rid': rid,
                        'type': full_type,
                        'name': element_name,
                        'bindings': bindings
                    })

            # Add binding info to XML as structured comments
            if binding_list:
                xml_lines.append(
                    '    <!-- ============================================ -->')
                xml_lines.append(
                    '    <!-- DATA BINDINGS (connects UI to game data)   -->')
                xml_lines.append(
                    '    <!-- Format: BindingType[rid=ID, name="..."]     -->')
                xml_lines.append(
                    '    <!--   key: value                               -->')
                xml_lines.append(
                    '    <!-- ============================================ -->')
                xml_lines.append('')

                # Limit to first 50 to avoid huge files
                for binding_info in binding_list[:50]:
                    rid = binding_info['rid']
                    b_type = binding_info['type'].split(
                        '/')[-1]  # Get just the class name
                    b_name = binding_info['name']

                    name_attr = f', name="{b_name}"' if b_name else ''
                    xml_lines.append(
                        f'    <!-- {b_type}[rid={rid}{name_attr}] -->')

                    for key, value in binding_info['bindings'].items():
                        if isinstance(value, list):
                            xml_lines.append(f'    <!--   {key}: -->')
                            for item in value[:10]:  # Limit list items
                                # Escape XML characters in value
                                item_escaped = str(item).replace('&', '&amp;').replace(
                                    '<', '&lt;').replace('>', '&gt;')
                                xml_lines.append(
                                    f'    <!--     - {item_escaped} -->')
                        else:
                            # Escape XML characters in value
                            value_escaped = str(value).replace('&', '&amp;').replace(
                                '<', '&lt;').replace('>', '&gt;')
                            xml_lines.append(
                                f'    <!--   {key}: {value_escaped} -->')
                    xml_lines.append('    <!--  -->')

                if len(binding_list) > 50:
                    xml_lines.append(
                        f'    <!-- ... and {len(binding_list) - 50} more bindings -->')

                xml_lines.append('')

    # Build element hierarchy
    element_map = {}
    template_map = {}  # Track templates by ID

    # Build element map
    for elem in elements:
        elem_id = getattr(elem, 'm_Id', None)
        if elem_id is not None:
            element_map[elem_id] = elem

    # Build template map
    if hasattr(data, 'm_TemplateAssets'):
        for tmpl in getattr(data, 'm_TemplateAssets', []):
            tmpl_id = getattr(tmpl, 'm_Id', None)
            if tmpl_id is not None:
                template_map[tmpl_id] = tmpl

    # Build binding lookup map (by uxmlAssetId which corresponds to element m_Id)
    binding_map = {}  # Key: element_id -> binding info
    if hasattr(data, 'references'):
        refs = getattr(data, 'references', None)
        if refs and hasattr(refs, 'RefIds'):
            ref_ids = getattr(refs, 'RefIds', [])

            for ref_obj in ref_ids:
                rid = getattr(ref_obj, 'rid', None)
                ref_type = getattr(ref_obj, 'type', None)
                ref_data = getattr(ref_obj, 'data', None)

                if rid is None or rid == -2 or not ref_data:
                    continue

                # Get uxmlAssetId which corresponds to element m_Id
                uxml_asset_id = getattr(ref_data, 'uxmlAssetId', None)

                # Extract bindings
                bindings = extract_bindings_from_serialized_data(ref_data)

                if bindings and uxml_asset_id is not None:
                    # Store by uxmlAssetId (which matches element m_Id)
                    binding_map[uxml_asset_id] = {
                        'rid': rid,
                        'bindings': bindings,
                        'element_name': getattr(ref_data, 'name', '')
                    }

    # Find root elements (no parent or parent not in map)
    root_elements = []
    for elem in elements:
        parent_id = getattr(elem, 'm_ParentId', None)
        if parent_id is None or parent_id == 0 or parent_id not in element_map:
            root_elements.append(elem)

    # Recursive function to build XML tree
    def build_element_xml(elem, indent=1):
        indent_str = '    ' * indent

        # Get element info
        elem_type_full = getattr(elem, 'm_FullTypeName', 'VisualElement')
        elem_name = getattr(elem, 'm_Name', '')
        elem_classes = getattr(elem, 'm_Classes', [])
        elem_text = getattr(elem, 'm_Text', '')
        elem_id = getattr(elem, 'm_Id', None)

        # Extract simple type name
        elem_type = elem_type_full
        if '.' in elem_type_full:
            elem_type = elem_type_full.split('.')[-1]

        # Check if it's a custom component (SI.* or FM.*)
        is_custom_component = elem_type_full.startswith(
            'SI.') or elem_type_full.startswith('FM.')

        lines = []

        # Add comment for custom components showing full qualified name
        if is_custom_component:
            lines.append(f"{indent_str}<!-- {elem_type_full} -->")

        # Add inline binding comment if this element has bindings
        if elem_id in binding_map:
            binding_info = binding_map[elem_id]
            bindings = binding_info['bindings']

            # Show most important bindings inline
            key_bindings = []
            for key, value in bindings.items():
                if isinstance(value, list):
                    if len(value) <= 3:
                        for item in value:
                            key_bindings.append(f"{key}: {item}")
                    else:
                        key_bindings.append(f"{key}: [{len(value)} items]")
                else:
                    key_bindings.append(f"{key}: {value}")

            if key_bindings:
                lines.append(
                    f"{indent_str}<!-- BINDING[rid={binding_info['rid']}]: {'; '.join(key_bindings[:3])} -->")
                if len(key_bindings) > 3:
                    lines.append(
                        f"{indent_str}<!--   ... and {len(key_bindings) - 3} more bindings -->")

        # Build opening tag
        tag = f"{indent_str}<{elem_type}"

        # Add attributes
        if elem_name:
            tag += f' name="{elem_name}"'

        if elem_classes:
            classes_str = ' '.join(elem_classes)
            tag += f' class="{classes_str}"'

        # Add element m_Id for binding preservation on re-import
        if elem_id is not None:
            tag += f' data-unity-id="{elem_id}"'

        # Check for properties (inline styles)
        properties = getattr(elem, 'm_Properties', [])
        if properties and len(properties) > 0:
            tag += ' style="/* inline styles */"'

        # Check for children (both regular elements and templates)
        children = [e for e in elements if getattr(
            e, 'm_ParentId', None) == elem_id]

        # Check for template children
        template_children = [t for t in template_map.values() if getattr(
            t, 'm_ParentId', None) == elem_id]

        if not children and not template_children and not elem_text:
            # Self-closing tag
            tag += ' />'
            lines.append(tag)
            return lines
        else:
            tag += '>'
            lines.append(tag)

            # Add text content
            if elem_text:
                lines.append(f"{indent_str}    {elem_text}")

            # Add template children first (they're typically includes)
            for tmpl in template_children:
                template_alias = getattr(
                    tmpl, 'm_TemplateAlias', 'UnknownTemplate')
                tmpl_classes = getattr(tmpl, 'm_Classes', [])
                class_attr = f' class="{" ".join(tmpl_classes)}"' if tmpl_classes else ''
                lines.append(
                    f"{indent_str}    <!-- Include: {template_alias} -->")
                lines.append(
                    f"{indent_str}    <Template src=\"{template_alias}\"{class_attr} />")

            # Add regular element children
            for child in children:
                lines.extend(build_element_xml(child, indent + 1))

            # Closing tag
            lines.append(f"{indent_str}</{elem_type}>")
            return lines

    # Build XML for all root elements
    for root_elem in root_elements:
        xml_lines.extend(build_element_xml(root_elem))

    xml_lines.append('</ui:UXML>')

    return '\n'.join(xml_lines)
