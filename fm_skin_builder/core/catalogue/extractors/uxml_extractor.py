"""
UXML Extractor

Extracts VisualTreeAsset assets from Unity bundles for the catalogue system.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Any, Optional, Set
import UnityPy
import hashlib

from .base import BaseAssetExtractor
from ..models import VisualTreeAsset
from ...uxml.uxml_exporter import UXMLExporter
from ...logger import get_logger

log = get_logger(__name__)


class UXMLExtractor(BaseAssetExtractor):
    """Extracts UXML/VisualTreeAsset assets from bundles."""

    def __init__(
        self,
        fm_version: str,
        export_uxml: bool = False,
        export_dir: Optional[Path] = None,
    ):
        """
        Initialize UXML extractor.

        Args:
            fm_version: FM version string
            export_uxml: Whether to export UXML files to disk
            export_dir: Directory to export UXML files (required if export_uxml=True)
        """
        super().__init__(fm_version)
        self.export_uxml = export_uxml
        self.export_dir = export_dir
        self.uxml_exporter = UXMLExporter()

        if export_uxml and not export_dir:
            raise ValueError("export_dir must be provided when export_uxml=True")

    def extract_from_bundle(self, bundle_path: Path) -> List[VisualTreeAsset]:
        """
        Extract VisualTreeAssets from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of VisualTreeAsset catalogue entries
        """
        import gc

        vta_assets = []

        try:
            env = UnityPy.load(str(bundle_path))
        except Exception as e:
            log.warning(f"Failed to load bundle {bundle_path.name}: {e}")
            return vta_assets

        bundle_name = bundle_path.name

        try:
            for obj in env.objects:
                # VisualTreeAssets are stored as MonoBehaviour
                if obj.type.name != "MonoBehaviour":
                    continue

                try:
                    data = obj.read()
                except Exception:
                    continue

                # Check if this is a VisualTreeAsset
                # VTA has m_VisualElementAssets field
                if not hasattr(data, "m_VisualElementAssets"):
                    continue

                name = self._get_asset_name(data)
                if not name:
                    continue

                try:
                    vta_entry = self._extract_vta_data(data, bundle_name, obj)
                    if vta_entry:
                        vta_assets.append(vta_entry)

                except Exception as e:
                    log.warning(f"Failed to extract VTA '{name}': {e}")
                    continue

        finally:
            # Clean up UnityPy environment
            try:
                del env
            except Exception:
                pass
            gc.collect()

        return vta_assets

    def _extract_vta_data(
        self, vta_data: Any, bundle_name: str, obj: Any
    ) -> Optional[VisualTreeAsset]:
        """
        Extract VisualTreeAsset data and metadata.

        Args:
            vta_data: Unity VisualTreeAsset object
            bundle_name: Name of the bundle
            obj: Unity object reference

        Returns:
            VisualTreeAsset catalogue entry or None
        """
        name = self._get_asset_name(vta_data)
        if not name:
            return None

        # Export UXML to get content hash and metadata
        try:
            uxml_doc = self.uxml_exporter.export_visual_tree_asset(vta_data)
        except Exception as e:
            log.warning(f"Failed to export VTA '{name}' to UXML: {e}")
            return None

        # Compute content hash from UXML document
        content_hash = self._compute_content_hash(uxml_doc, vta_data)

        # Gather statistics
        element_count, element_types, classes_used = self._gather_statistics(uxml_doc)

        # Get template references
        templates_used = [t.name for t in uxml_doc.templates]

        # Check for inline styles
        has_inline_styles = (
            uxml_doc.inline_styles is not None and len(uxml_doc.inline_styles) > 0
        )

        # Generate tags
        tags = self._generate_tags(name, element_types, classes_used)

        # Export UXML file if requested
        export_path = None
        if self.export_uxml and self.export_dir:
            export_path = self._export_uxml_file(uxml_doc, name)

        # Create catalogue entry
        vta_entry = VisualTreeAsset(
            name=name,
            bundle=bundle_name,
            content_hash=content_hash,
            element_count=element_count,
            element_types=element_types,
            classes_used=classes_used,
            templates_used=templates_used,
            has_inline_styles=has_inline_styles,
            tags=tags,
            export_path=export_path,
            **self._create_default_status(),
        )

        return vta_entry

    def _compute_content_hash(self, uxml_doc: Any, vta_data: Any) -> str:
        """
        Compute content hash for UXML.

        Args:
            uxml_doc: UXMLDocument object
            vta_data: Unity VTA data

        Returns:
            SHA256 hash string
        """
        # Create a stable representation for hashing
        # Include element structure, attributes, and inline styles

        hash_parts = []

        # Add elements recursively
        def add_element(elem):
            if not elem:
                return

            # Add element type
            hash_parts.append(f"type:{elem.element_type}")

            # Add attributes (sorted for stability)
            for attr in sorted(elem.attributes, key=lambda a: a.name):
                hash_parts.append(f"attr:{attr.name}={attr.value}")

            # Add text
            if elem.text:
                hash_parts.append(f"text:{elem.text}")

            # Add children
            for child in elem.children:
                add_element(child)

        if uxml_doc.root:
            add_element(uxml_doc.root)

        # Add inline styles
        if uxml_doc.inline_styles:
            hash_parts.append(f"styles:{uxml_doc.inline_styles}")

        # Compute hash
        hash_content = "\n".join(hash_parts).encode("utf-8")
        return hashlib.sha256(hash_content).hexdigest()

    def _gather_statistics(self, uxml_doc: Any) -> tuple:
        """
        Gather statistics from UXML document.

        Args:
            uxml_doc: UXMLDocument object

        Returns:
            Tuple of (element_count, element_types, classes_used)
        """
        element_count = 0
        element_types: Set[str] = set()
        classes_used: Set[str] = set()

        all_elements = uxml_doc.get_all_elements()
        element_count = len(all_elements)

        for elem in all_elements:
            element_types.add(elem.element_type)

            # Gather classes
            for cls in elem.get_classes():
                classes_used.add(cls)

        return (element_count, sorted(list(element_types)), sorted(list(classes_used)))

    def _generate_tags(
        self, name: str, element_types: List[str], classes_used: List[str]
    ) -> List[str]:
        """
        Generate auto-tags for VTA.

        Args:
            name: Asset name
            element_types: List of element types used
            classes_used: List of CSS classes used

        Returns:
            List of tags
        """
        tags = ["uxml", "ui"]

        # Add tag based on name
        name_lower = name.lower()

        if "menu" in name_lower:
            tags.append("menu")
        if "screen" in name_lower or "panel" in name_lower:
            tags.append("screen")
        if "dialog" in name_lower or "popup" in name_lower:
            tags.append("dialog")
        if "button" in name_lower:
            tags.append("button")
        if "list" in name_lower or "table" in name_lower:
            tags.append("list")

        # Add tags based on element types
        if "ListView" in element_types or "TreeView" in element_types:
            tags.append("list")
        if "ScrollView" in element_types:
            tags.append("scrollable")
        if "Image" in element_types:
            tags.append("image")

        return sorted(list(set(tags)))

    def _export_uxml_file(self, uxml_doc: Any, name: str) -> str:
        """
        Export UXML to file.

        Args:
            uxml_doc: UXMLDocument object
            name: Asset name

        Returns:
            Relative export path
        """
        # Create export directory
        uxml_dir = self.export_dir / "uxml"
        uxml_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename (sanitize name)
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
        output_path = uxml_dir / f"{safe_name}.uxml"

        # Export
        try:
            self.uxml_exporter.write_uxml(uxml_doc, output_path)

            # Return relative path
            return str(output_path.relative_to(self.export_dir))

        except Exception as e:
            log.warning(f"Failed to write UXML file for '{name}': {e}")
            return None
