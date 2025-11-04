#!/usr/bin/env python3
"""Build a CSS ↔ UXML cross-reference catalog from Unity bundles.

This MVP script extracts:
- CSS variables and their definitions/usage
- CSS classes and their definitions/usage
- UXML files and their stylesheet references, classes used, and inline styles

The output is a JSON catalog that powers the searchable HTML explorer.

Usage:
    # Scan all bundles in a directory
    python scripts/build_css_uxml_catalog.py --bundle-dir bundles --output extracted_sprites/css_uxml_catalog.json

    # Scan specific bundles
    python scripts/build_css_uxml_catalog.py --bundle bundles/ui-styles_assets_common.bundle --output catalog.json
"""

from src.utils.uxml_parser import extract_strings_with_offsets, detect_class_or_style, parse_visual_tree_asset, visual_tree_asset_to_xml
from src.core.css_patcher import build_selector_from_parts, serialize_stylesheet_to_uss
from src.core.logger import get_logger
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import re

import UnityPy

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


log = get_logger(__name__)


class CSSUXMLCatalog:
    """Catalog for CSS and UXML cross-references."""

    def __init__(self):
        # CSS Variables
        self.css_variables: Dict[str, Dict[str, Any]] = {}
        # CSS Classes/Selectors
        self.css_classes: Dict[str, Dict[str, Any]] = {}
        # UXML Files
        self.uxml_files: Dict[str, Dict[str, Any]] = {}
        # StyleSheets
        self.stylesheets: Dict[str, Dict[str, Any]] = {}
        # Component tracking
        # component_type -> usage info
        self.components: Dict[str, Dict[str, Any]] = {}
        self.component_namespace_stats: Dict[str, int] = defaultdict(
            int)  # namespace -> count
        # NEW: Template tracking (UXML composition)
        # template_alias -> usage info
        self.templates: Dict[str, Dict[str, Any]] = {}

    def add_stylesheet(self, name: str, bundle: str, data: Any):
        """Extract CSS variables and classes from a StyleSheet."""
        if name in self.stylesheets:
            return  # Already processed

        strings = list(getattr(data, "strings", []))
        colors = getattr(data, "colors", [])
        rules = getattr(data, "m_Rules", [])

        # Build rule selectors
        rule_selectors = self._safe_rule_selectors(data)

        # Initialize stylesheet entry
        sheet_entry = {
            "bundle": bundle,
            "variables_defined": [],
            "classes_defined": [],
            "properties": {}  # selector -> property list
        }

        # Extract CSS variables from strings
        for s in strings:
            if isinstance(s, str) and s.startswith("--"):
                sheet_entry["variables_defined"].append(s)
                # Add to global variable catalog
                if s not in self.css_variables:
                    self.css_variables[s] = {
                        "defined_in": [],
                        "used_in_stylesheets": [],
                        "used_in_uxml": [],
                        "value": None  # Will try to extract
                    }
                if name not in self.css_variables[s]["defined_in"]:
                    self.css_variables[s]["defined_in"].append(name)

        # Extract classes/selectors and properties
        for i, rule in enumerate(rules):
            selectors = rule_selectors.get(i, [])
            properties = []

            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if not prop_name:
                    continue

                # Extract property values
                prop_values = []
                for val in getattr(prop, "m_Values", []):
                    vt = getattr(val, "m_ValueType", None)
                    vi = getattr(val, "valueIndex", None)

                    if vt in (3, 8, 10) and isinstance(vi, int) and 0 <= vi < len(strings):
                        # String/variable reference
                        string_val = strings[vi]
                        prop_values.append(
                            {"type": "string", "value": string_val})

                        # Track variable usage
                        if isinstance(string_val, str) and string_val.startswith("--"):
                            if string_val in self.css_variables:
                                if name not in self.css_variables[string_val]["used_in_stylesheets"]:
                                    self.css_variables[string_val]["used_in_stylesheets"].append(
                                        name)

                    elif vt == 4 and isinstance(vi, int) and 0 <= vi < len(colors):
                        # Color value
                        c = colors[vi]
                        color_hex = f"#{int(c.r*255):02x}{int(c.g*255):02x}{int(c.b*255):02x}"
                        if c.a < 1.0:
                            color_hex += f"{int(c.a*255):02x}"
                        prop_values.append(
                            {"type": "color", "value": color_hex})

                    elif vt == 1:  # Float/number
                        prop_values.append({"type": "number", "value": vi})

                properties.append({
                    "name": prop_name,
                    "values": prop_values
                })

            # Store properties for this selector
            for selector in selectors:
                if selector not in sheet_entry["properties"]:
                    sheet_entry["properties"][selector] = []
                sheet_entry["properties"][selector].extend(properties)

                # Add selector to catalog
                if selector not in self.css_classes:
                    self.css_classes[selector] = {
                        "defined_in": [],
                        "used_in_uxml": [],
                        "properties": {}
                    }

                if name not in self.css_classes[selector]["defined_in"]:
                    self.css_classes[selector]["defined_in"].append(name)

                # Store a sample of properties for this selector
                for prop in properties:
                    self.css_classes[selector]["properties"][prop["name"]
                                                             ] = prop["values"]

                # Track which stylesheet defines this class
                sheet_entry["classes_defined"].append(selector)

        self.stylesheets[name] = sheet_entry

    def add_stylesheet_export_path(self, name: str, export_path: str):
        """Add export file path to stylesheet entry."""
        if name in self.stylesheets:
            self.stylesheets[name]["export_path"] = export_path

    def add_uxml_export_path(self, name: str, export_path: str):
        """Add export file path to UXML entry."""
        if name in self.uxml_files:
            self.uxml_files[name]["export_path"] = export_path

    def add_uxml_from_visual_tree(self, name: str, uxml_data: Dict[str, Any]):
        """Add UXML from parsed VisualTreeAsset."""
        if name in self.uxml_files:
            return  # Already processed

        # Store the UXML data
        self.uxml_files[name] = uxml_data

        # Update global catalogs with cross-references
        classes = uxml_data.get("classes_used", [])
        variables = uxml_data.get("variables_used", [])

        for cls in classes:
            if cls in self.css_classes:
                if name not in self.css_classes[cls]["used_in_uxml"]:
                    self.css_classes[cls]["used_in_uxml"].append(name)

        for var in variables:
            if var in self.css_variables:
                if name not in self.css_variables[var]["used_in_uxml"]:
                    self.css_variables[var]["used_in_uxml"].append(name)

        # Track component usage
        component_types = uxml_data.get("component_types", [])
        for comp_type in component_types:
            if comp_type not in self.components:
                self.components[comp_type] = {
                    "used_in_uxml": [],
                    "is_custom": comp_type.startswith("SI.") or comp_type.startswith("FM."),
                    "namespace": comp_type.rsplit(".", 1)[0] if "." in comp_type else "root"
                }
            if name not in self.components[comp_type]["used_in_uxml"]:
                self.components[comp_type]["used_in_uxml"].append(name)

            # Track namespace statistics
            namespace = self.components[comp_type]["namespace"]
            self.component_namespace_stats[namespace] += 1

        # NEW: Track template usage (UXML composition)
        templates_used = uxml_data.get("templates_used", [])
        for template_alias in templates_used:
            if template_alias not in self.templates:
                self.templates[template_alias] = {
                    "used_in_uxml": [],
                    "is_template": True  # This is a reusable UXML component
                }
            if name not in self.templates[template_alias]["used_in_uxml"]:
                self.templates[template_alias]["used_in_uxml"].append(name)

    def add_uxml_file(self, name: str, bundle: str, content: bytes):
        """Extract classes, variables, and stylesheet references from UXML content (TextAsset format)."""
        if name in self.uxml_files:
            return  # Already processed

        uxml_entry = {
            "bundle": bundle,
            "stylesheets": [],
            "has_inline_styles": False,
            "classes_used": [],
            "variables_used": [],
            "elements": []
        }

        # Convert bytes to string
        try:
            text = content.decode('utf-8', errors='ignore')
        except:
            text = str(content)

        # Extract stylesheet references (e.g., <Style src="..." />)
        stylesheet_refs = re.findall(
            r'<Style\s+src="([^"]+)"', text, re.IGNORECASE)
        uxml_entry["stylesheets"] = list(set(stylesheet_refs))

        # Detect inline styles
        if re.search(r'style\s*=\s*"[^"]+"', text, re.IGNORECASE):
            uxml_entry["has_inline_styles"] = True

        # Extract class names (e.g., class="foo bar")
        class_matches = re.findall(
            r'class\s*=\s*"([^"]+)"', text, re.IGNORECASE)
        classes = set()
        for match in class_matches:
            # Split multiple classes
            for cls in match.split():
                # Skip Unity built-in classes for now
                if cls and not cls.startswith("unity-"):
                    # Normalize to .class format
                    cls_normalized = cls if cls.startswith(".") else f".{cls}"
                    classes.add(cls_normalized)
        uxml_entry["classes_used"] = sorted(list(classes))

        # Extract CSS variable usage (e.g., var(--primary))
        var_matches = re.findall(r'var\((--[a-zA-Z0-9_-]+)\)', text)
        variables = set(var_matches)
        uxml_entry["variables_used"] = sorted(list(variables))

        # Extract element types (e.g., <Button>, <Label>)
        element_matches = re.findall(r'<([A-Z][a-zA-Z0-9_]+)', text)
        elements = set(element_matches)
        uxml_entry["elements"] = sorted(list(elements))

        # Update global catalogs
        for cls in classes:
            if cls in self.css_classes:
                if name not in self.css_classes[cls]["used_in_uxml"]:
                    self.css_classes[cls]["used_in_uxml"].append(name)

        for var in variables:
            if var in self.css_variables:
                if name not in self.css_variables[var]["used_in_uxml"]:
                    self.css_variables[var]["used_in_uxml"].append(name)

        self.uxml_files[name] = uxml_entry

    def _safe_rule_selectors(self, data) -> Dict[int, List[str]]:
        """Extract selectors for each rule in a stylesheet."""
        rules = getattr(data, "m_Rules", [])
        selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
            data, "m_ComplexSelectors") else []
        out: Dict[int, List[str]] = {i: [] for i in range(len(rules))}

        for sel in selectors:
            rule_idx = getattr(sel, "ruleIndex", -1)
            if 0 <= rule_idx < len(rules):
                for s in getattr(sel, "m_Selectors", []) or []:
                    parts = getattr(s, "m_Parts", [])
                    out[rule_idx].append(build_selector_from_parts(parts))

        # Fallback names for empty selectors
        for i in range(len(rules)):
            if not out[i]:
                out[i] = [f".rule-{i}"]

        return out

    def to_dict(self) -> Dict[str, Any]:
        """Export catalog as dictionary."""
        return {
            "css_variables": self.css_variables,
            "css_classes": self.css_classes,
            "uxml_files": self.uxml_files,
            "stylesheets": self.stylesheets,
            # Component tracking
            "components": self.components,
            "component_stats": {
                "total_unique_types": len(self.components),
                "custom_components": sum(1 for c in self.components.values() if c["is_custom"]),
                "by_namespace": dict(self.component_namespace_stats)
            },
            # NEW: Template tracking (UXML composition)
            "templates": self.templates,
            "template_stats": {
                "total_templates": len(self.templates),
                "files_using_templates": sum(1 for f in self.uxml_files.values() if f.get("template_count", 0) > 0)
            }
        }


def scan_bundle_for_catalog(bundle_path: Path, catalog: CSSUXMLCatalog, export_dir: Optional[Path] = None, verbose: bool = False):
    """Scan a single bundle and add to catalog.

    Args:
        bundle_path: Path to the bundle file
        catalog: CSSUXMLCatalog to populate
        export_dir: Optional directory to export USS/UXML files
        verbose: Enable verbose logging
    """
    bundle_name = bundle_path.name

    if verbose:
        log.info(f"Scanning: {bundle_path}")

    try:
        env = UnityPy.load(str(bundle_path))
    except Exception as e:
        log.error(f"Failed to load bundle {bundle_path}: {e}")
        return

    stylesheets_found = 0
    uxml_found = 0

    # Create export directories if needed
    uss_export_dir = None
    uxml_export_dir = None
    if export_dir:
        uss_export_dir = export_dir / "uss"
        uxml_export_dir = export_dir / "uxml"
        uss_export_dir.mkdir(parents=True, exist_ok=True)
        uxml_export_dir.mkdir(parents=True, exist_ok=True)

    # Scan all MonoBehaviour objects
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue

        try:
            data = obj.read()
        except:
            continue

        name = getattr(data, "m_Name", "Unnamed")

        # Check if it's a StyleSheet (has colors and strings)
        if hasattr(data, "colors") and hasattr(data, "strings"):
            catalog.add_stylesheet(name, bundle_name, data)
            stylesheets_found += 1

            # Export USS file
            if uss_export_dir:
                try:
                    uss_content = serialize_stylesheet_to_uss(data)
                    uss_file = uss_export_dir / f"{name}.uss"
                    uss_file.write_text(uss_content, encoding='utf-8')
                    # Add export path to catalog (relative to HTML file location)
                    catalog.add_stylesheet_export_path(
                        name, f"exports/uss/{name}.uss")
                except Exception as e:
                    if verbose:
                        log.warning(f"Failed to export USS for {name}: {e}")
            continue

        # Check if it's a VisualTreeAsset (has m_VisualElementAssets)
        if hasattr(data, "m_VisualElementAssets"):
            uxml_doc = parse_visual_tree_asset(data, name, bundle_name)
            if uxml_doc:
                # Convert to dict and add to catalog
                uxml_dict = uxml_doc.to_dict()
                catalog.add_uxml_from_visual_tree(name, uxml_dict)
                uxml_found += 1

                # Export UXML file
                if uxml_export_dir:
                    try:
                        uxml_content = visual_tree_asset_to_xml(data, name)
                        uxml_file = uxml_export_dir / f"{name}.uxml"
                        uxml_file.write_text(uxml_content, encoding='utf-8')
                        # Add export path to catalog (relative to HTML file location)
                        catalog.add_uxml_export_path(
                            name, f"exports/uxml/{name}.uxml")
                    except Exception as e:
                        if verbose:
                            log.warning(
                                f"Failed to export UXML for {name}: {e}")
                continue

    # Also check TextAsset for XML-based UXML (legacy format)
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue

        try:
            data = obj.read()
        except:
            continue

        name = getattr(data, "m_Name", None) or getattr(
            data, "name", "UnnamedUXML")

        # Check if it's likely UXML (has XML-like content)
        script = getattr(data, "m_Script", b"") or getattr(data, "script", b"")
        if not script:
            continue

        # Simple heuristic: check for UXML markers
        try:
            text_preview = script[:500].decode(
                'utf-8', errors='ignore').lower()
        except:
            continue

        if not any(marker in text_preview for marker in ['<ui:', '<style', 'visualelement', 'uxml']):
            continue

        catalog.add_uxml_file(name, bundle_name, script)
        uxml_found += 1

        # Export UXML file
        if uxml_export_dir:
            try:
                uxml_content = script.decode(
                    'utf-8', errors='ignore') if isinstance(script, bytes) else script
                uxml_file = uxml_export_dir / f"{name}.uxml"
                uxml_file.write_text(uxml_content, encoding='utf-8')
                catalog.add_uxml_export_path(name, f"uxml/{name}.uxml")
            except Exception as e:
                if verbose:
                    log.warning(f"Failed to export UXML for {name}: {e}")

    if verbose:
        log.info(
            f"  Found {stylesheets_found} stylesheets, {uxml_found} UXML files")


def build_catalog(bundle_paths: List[Path], output_path: Path, export_files: bool = False, verbose: bool = False):
    """Build the full catalog from multiple bundles.

    Args:
        bundle_paths: List of bundle files to scan
        output_path: Path to output JSON catalog
        export_files: If True, export USS/UXML to human-readable formats
        verbose: Enable verbose logging
    """
    catalog = CSSUXMLCatalog()

    # Determine export directory
    export_dir = None
    if export_files:
        export_dir = output_path.parent / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

    for bundle_path in bundle_paths:
        scan_bundle_for_catalog(bundle_path, catalog, export_dir, verbose)

    # Export to JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(catalog.to_dict(), f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n✓ Catalog built successfully!")
    print(f"  Output: {output_path}")
    print(f"\n📊 Summary:")
    print(f"  CSS Variables: {len(catalog.css_variables)}")
    print(f"  CSS Classes: {len(catalog.css_classes)}")
    print(f"  UXML Files: {len(catalog.uxml_files)}")
    print(f"  Stylesheets: {len(catalog.stylesheets)}")

    # Show some examples
    if catalog.css_variables:
        print(f"\n  Example variables:")
        for var in list(catalog.css_variables.keys())[:5]:
            defined_in = catalog.css_variables[var]["defined_in"]
            print(f"    {var} (defined in {len(defined_in)} stylesheets)")

    if catalog.css_classes:
        print(f"\n  Example classes:")
        for cls in list(catalog.css_classes.keys())[:5]:
            used_in = catalog.css_classes[cls]["used_in_uxml"]
            print(f"    {cls} (used in {len(used_in)} UXML files)")


def main():
    parser = argparse.ArgumentParser(
        description="Build CSS ↔ UXML cross-reference catalog from Unity bundles"
    )
    parser.add_argument(
        "--bundle",
        "-b",
        type=Path,
        action="append",
        help="Bundle file to scan (can be specified multiple times)"
    )
    parser.add_argument(
        "--bundle-dir",
        "-d",
        type=Path,
        help="Directory containing bundles to scan (scans all .bundle files)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("extracted_sprites/css_uxml_catalog.json"),
        help="Output JSON catalog file (default: extracted_sprites/css_uxml_catalog.json)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--export-files",
        "-e",
        action="store_true",
        help="Export USS and UXML to human-readable formats (creates exports/uss and exports/uxml directories)"
    )

    args = parser.parse_args()

    # Collect bundle paths
    bundle_paths = []

    if args.bundle:
        for bundle in args.bundle:
            if not bundle.exists():
                print(f"Error: Bundle not found: {bundle}")
                return 1
            bundle_paths.append(bundle)

    if args.bundle_dir:
        if not args.bundle_dir.exists():
            print(f"Error: Bundle directory not found: {args.bundle_dir}")
            return 1
        for bundle in sorted(args.bundle_dir.glob("*.bundle")):
            bundle_paths.append(bundle)

    if not bundle_paths:
        print("Error: No bundles specified. Use --bundle or --bundle-dir")
        parser.print_help()
        return 1

    print(f"🔍 Scanning {len(bundle_paths)} bundle(s)...")
    if args.export_files:
        print(
            f"📄 Exporting USS and UXML files to {args.output.parent / 'exports'}")
    build_catalog(bundle_paths, args.output, args.export_files, args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
