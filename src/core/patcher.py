"""Core patching logic applying skin overrides."""
from pathlib import Path
from .bundle_manager import BundleManager
from .skin_config import SkinConfig
from .logger import get_logger

logger = get_logger(__name__)

def apply_overrides(skin_dir: Path, out_dir: Path) -> None:
    config = SkinConfig(skin_dir / "config.json")
    config.load()
    bundle = BundleManager(Path(config.data["target_bundle"]))
    for internal_path, local_file in config.overrides.items():
        src = skin_dir / local_file
        bundle.replace_asset(internal_path, src)
    bundle.save(out_dir / config.data["output_bundle"])
