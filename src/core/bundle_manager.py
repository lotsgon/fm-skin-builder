from __future__ import annotations
from pathlib import Path
from .logger import get_logger

logger = get_logger(__name__)

class BundleManager:
    """Abstracts Unity bundle operations (stub)."""
    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path

    def list_assets(self) -> list[str]:
        return []

    def replace_asset(self, internal_path: str, new_file: Path) -> bool:
        logger.info(f"Replace {internal_path} <- {new_file}")
        return True

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saved new bundle to {output_path}")
