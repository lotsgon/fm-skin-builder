"""
DEPRECATED: Legacy UXML string extraction utilities.

This module has been replaced by the comprehensive UXML import/export pipeline
in fm_skin_builder.core.uxml.

For proper UXML export/import, use:
    from fm_skin_builder.core.uxml import UXMLExporter, UXMLImporter

The old string-based approach was unreliable and is no longer maintained.
"""

from __future__ import annotations
import warnings
from fm_skin_builder.core.uxml import (
    UXMLExporter,
    UXMLImporter,
    UXMLDocument,
    UXMLElement,
    UXMLAttribute,
    StyleParser,
    StyleSerializer,
)

warnings.warn(
    "fm_skin_builder.utils.uxml_parser is deprecated. "
    "Use fm_skin_builder.core.uxml instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "UXMLExporter",
    "UXMLImporter",
    "UXMLDocument",
    "UXMLElement",
    "UXMLAttribute",
    "StyleParser",
    "StyleSerializer",
]
