from __future__ import annotations
from pathlib import Path
from .bundle_manager import BundleManager
from .cache import load_or_cache_config
from .logger import get_logger
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

    out = out_dir / model.output_bundle
    bundle.save(out)
    log.info(f"Build complete: {out}")
