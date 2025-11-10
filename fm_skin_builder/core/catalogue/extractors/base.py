"""
Base extractor interface for asset extraction.

All extractors follow a common pattern for extracting assets from Unity bundles.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Any, Dict
from ..models import AssetStatus


class BaseAssetExtractor(ABC):
    """Base class for all asset extractors."""

    def __init__(self, fm_version: str):
        """
        Initialize extractor.

        Args:
            fm_version: FM version string (e.g., "2026.4.0")
        """
        self.fm_version = fm_version

    @abstractmethod
    def extract_from_bundle(self, bundle_path: Path) -> List[Any]:
        """
        Extract assets from a Unity bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of extracted asset objects (model instances)
        """
        pass

    def _get_asset_name(self, data: Any) -> str | None:
        """
        Get asset name from Unity object.

        Args:
            data: Unity asset data

        Returns:
            Asset name or None if not found
        """
        return getattr(data, "m_Name", None) or getattr(data, "name", None)

    def _create_default_status(self) -> Dict[str, Any]:
        """
        Create default version tracking fields.

        Returns:
            Dictionary with status, first_seen, last_seen
        """
        return {
            "status": AssetStatus.ACTIVE,
            "first_seen": self.fm_version,
            "last_seen": self.fm_version,
        }
