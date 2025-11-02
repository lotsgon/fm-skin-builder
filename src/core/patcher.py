from __future__ import annotations
from pathlib import Path
from .bundle_manager import BundleManager
from .cache import load_or_cache_config
from .logger import get_logger

log = get_logger(__name__)

def apply_overrides(skin_dir: Path, out_dir: Path) -> None:
    model = load_or_cache_config(skin_dir)
    bundle = BundleManager(Path(model.target_bundle))

    for internal, local in model.overrides.items():
        src = skin_dir / local
        if not src.exists():
            log.warning(f"Missing local file: {src}")
            continue
        bundle.replace_asset(internal, src)

    out = out_dir / model.output_bundle
    bundle.save(out)
    log.info(f"Build complete: {out}")
