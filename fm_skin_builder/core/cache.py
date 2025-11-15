from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
from .logger import get_logger
from .skin_config import SkinConfig, SkinConfigModel

log = get_logger(__name__)


def _hash_config(config_path: Path) -> str:
    raw = config_path.read_bytes()
    return hashlib.sha256(raw + str(config_path.stat().st_mtime_ns).encode()).hexdigest()


def cache_dir(root: Path) -> Path:
    """
    Get the cache directory for skin configurations.

    Checks FM_CACHE_DIR environment variable first, otherwise falls back
    to .cache/skins in the project root.
    """
    env_cache = os.environ.get("FM_CACHE_DIR")
    if env_cache:
        cache_path = Path(env_cache)
        log.debug(f"Using cache directory from FM_CACHE_DIR: {cache_path}")
        return cache_path

    # Fallback to old behavior
    return root / ".cache" / "skins"


def load_or_cache_config(skin_dir: Path) -> SkinConfigModel:
    cfg_path = skin_dir / "config.json"
    h = _hash_config(cfg_path)
    # root is repo root = skin_dir.parent.parent (since skin_dir = repo/skins/name)
    cdir = cache_dir(root=skin_dir.parent.parent) / skin_dir.name
    cdir.mkdir(parents=True, exist_ok=True)
    target = cdir / f"{h}.json"

    if target.exists():
        log.info(f"Using cached config: {target.name}")
        data = json.loads(target.read_text(encoding="utf-8"))
        return SkinConfigModel.model_validate(data)

    log.info("Parsing and caching config...")
    cfg = SkinConfig(cfg_path).load()
    target.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
    return cfg
