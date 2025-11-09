from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import UnityPy
from .logger import get_logger

logger = get_logger(__name__)


class BundleManager:
    """Manages Unity bundle operations using UnityPy."""

    def __init__(self, bundle_path: Path):
        self.bundle_path = bundle_path
        self.env: Optional[UnityPy.Environment] = None
        self.modified = False

    def load_bundle(self) -> None:
        """Load the Unity bundle."""
        if self.env is None:
            logger.info(f"Loading bundle: {self.bundle_path}")
            self.env = UnityPy.load(str(self.bundle_path))

    def list_assets(self) -> list[str]:
        """List asset names in the bundle."""
        if self.env is None:
            self.load_bundle()
        assets = []
        for obj in self.env.objects:
            if obj.type.name == "MonoBehaviour":
                data = obj.read()
                name = getattr(data, "m_Name", None)
                if name:
                    assets.append(name)
        return assets

    def replace_asset(self, internal_path: str, new_file: Path) -> bool:
        """Replace an asset in the bundle (for fonts, etc.)."""
        if self.env is None:
            self.load_bundle()
        replaced = False
        for obj in self.env.objects:
            if obj.type.name == "Font":
                data = obj.read()
                if getattr(data, "m_Name", None) == internal_path:
                    font_bytes = new_file.read_bytes()
                    data.m_FontData = font_bytes
                    obj.save_typetree(data)
                    logger.info(f"Replaced font data for {internal_path}")
                    replaced = True
                    self.modified = True
        return replaced

    def patch_stylesheet_colors(self, css_overrides: Dict[str, str]) -> None:
        """Patch stylesheet colors based on CSS variable overrides."""
        if self.env is None:
            self.load_bundle()
        logger.info("Patching stylesheet colors")
        for obj in self.env.objects:
            if obj.type.name == "MonoBehaviour":
                data = obj.read()
                if not hasattr(data, "colors") or not hasattr(data, "strings"):
                    continue
                name = getattr(data, "m_Name", "UnnamedStyleSheet")
                self._patch_single_stylesheet(data, css_overrides, name)
                if self._was_modified(data):
                    self.modified = True

    def _patch_single_stylesheet(self, data, css_vars: Dict[str, str], name: str) -> None:
        """Patch a single stylesheet's colors."""
        colors = getattr(data, "colors", [])
        strings = getattr(data, "strings", [])
        rules = getattr(data, "m_Rules", [])

        # Patch direct property matches
        for rule in rules:
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                if prop_name in css_vars:
                    for val in getattr(prop, "m_Values", []):
                        if getattr(val, "m_ValueType", None) == 4:
                            value_index = getattr(val, "valueIndex", None)
                            if value_index is not None and 0 <= value_index < len(colors):
                                hex_val = css_vars[prop_name]
                                r, g, b, a = self._hex_to_rgba(hex_val)
                                col = colors[value_index]
                                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                                    col.r, col.g, col.b, col.a = r, g, b, a
                                    logger.info(f"Patched {name}: {prop_name} -> {hex_val}")

        # Patch CSS variables
        for color_idx, color in enumerate(colors):
            if color_idx >= len(strings):
                continue
            var_name = strings[color_idx]
            if var_name in css_vars:
                hex_val = css_vars[var_name]
                r, g, b, a = self._hex_to_rgba(hex_val)
                col = colors[color_idx]
                if (col.r, col.g, col.b, col.a) != (r, g, b, a):
                    col.r, col.g, col.b, col.a = r, g, b, a
                    logger.info(f"Patched {name}: {var_name} -> {hex_val}")

        data.save()

    def _hex_to_rgba(self, hex_str: str) -> tuple:
        """Convert hex to RGBA floats."""
        hex_str = hex_str.lstrip("#")
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        a = int(hex_str[6:8], 16) / 255.0 if len(hex_str) == 8 else 1.0
        return r, g, b, a

    def _was_modified(self, data) -> bool:
        """Check if data was modified (simplified)."""
        return True  # For now, assume yes

    def save(self, output_path: Path) -> None:
        """Save the modified bundle."""
        if self.env is None:
            logger.warning("No bundle loaded")
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(self.env.file.save())
        logger.info(f"Saved bundle to {output_path}")
