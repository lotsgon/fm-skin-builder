from __future__ import annotations
from pathlib import Path
from .bundle_manager import BundleManager
from .cache import load_or_cache_config
from .logger import get_logger
from ..utils.uxml_importer import UXMLImporter
import re

log = get_logger(__name__)


def load_css_vars(css_path: Path) -> dict:
    """Parse a .css/.uss file for --var: #hex; pairs"""
    text = css_path.read_text(encoding="utf-8")
    matches = re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6,8});", text)
    css = {f"--{k}": v for k, v in matches}
    log.info(f"Loaded {len(css)} CSS variables from {css_path}")
    return css


def apply_overrides(skin_dir: Path, out_dir: Path) -> None:
    model = load_or_cache_config(skin_dir)
    bundle = BundleManager(Path(model.target_bundle))

    # Load CSS variables from colours/ directory
    colours_dir = skin_dir / "colours"
    css_vars = {}
    if colours_dir.exists():
        for css_file in colours_dir.glob("*.uss"):
            css_vars.update(load_css_vars(css_file))

    # Patch stylesheet colors if any CSS vars found
    if css_vars:
        bundle.patch_stylesheet_colors(css_vars)

    # Apply asset overrides
    for internal, local in model.overrides.items():
        src = skin_dir / local
        if not src.exists():
            log.warning(f"Missing local file: {src}")
            continue
        bundle.replace_asset(internal, src)

    # Apply UXML overrides
    if model.uxml_overrides:
        importer = UXMLImporter()
        for asset_name, local_path in model.uxml_overrides.items():
            uxml_file = skin_dir / local_path
            if not uxml_file.exists():
                log.warning(f"Missing UXML file: {uxml_file}")
                continue

            try:
                log.info(f"Importing UXML: {asset_name} from {local_path}")
                uxml_data = importer.parse_uxml_file(str(uxml_file))

                # Check for validation errors
                validation = importer.get_validation_report()
                if "Error" in validation:
                    log.error(f"UXML validation failed for {asset_name}:")
                    log.error(validation)
                    continue

                # Update the bundle
                if bundle.update_uxml_asset(asset_name, uxml_data):
                    log.info(f"✓ Applied UXML override: {asset_name}")
                else:
                    log.warning(
                        f"✗ Failed to apply UXML override: {asset_name}")

            except Exception as e:
                log.error(f"Failed to import UXML {asset_name}: {e}")
                continue

    out = out_dir / model.output_bundle
    bundle.save(out)
    log.info(f"Build complete: {out}")
