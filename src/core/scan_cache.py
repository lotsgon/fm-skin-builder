from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from .logger import get_logger
from .cache import cache_dir
from .css_sources import CollectedCss

log = get_logger(__name__)

SCAN_INDEX_VERSION = 1


def _bundle_fingerprint(path: Path) -> Dict[str, Any]:
    try:
        st = path.stat()
        return {"path": str(path), "mtime": int(st.st_mtime), "size": int(st.st_size)}
    except Exception:
        return {"path": str(path), "mtime": None, "size": None}


def _cache_index_path(cache_skin_dir: Path, bundle: Path) -> Path:
    return cache_skin_dir / f"{bundle.stem}.index.json"


def _is_index_valid(idx: Dict[str, Any], bundle: Path) -> bool:
    meta = idx.get("_meta", {})
    if meta.get("version") != SCAN_INDEX_VERSION:
        return False
    fp = meta.get("fingerprint", {})
    st = bundle.stat()
    return (
        fp.get("path") == str(bundle)
        and isinstance(fp.get("mtime"), int)
        and isinstance(fp.get("size"), int)
        and fp.get("mtime") == int(st.st_mtime)
        and fp.get("size") == int(st.st_size)
    )


def load_scan_index(cache_skin_dir: Path, bundle: Path) -> Optional[Dict[str, Any]]:
    path = _cache_index_path(cache_skin_dir, bundle)
    if not path.exists():
        return None
    try:
        idx = json.loads(path.read_text(encoding="utf-8"))
        if _is_index_valid(idx, bundle):
            log.debug(f"Using cached scan index: {path}")
            return idx
    except Exception:
        return None
    return None


def _save_scan_index(cache_skin_dir: Path, bundle: Path, index: Dict[str, Any]) -> Path:
    path = _cache_index_path(cache_skin_dir, bundle)
    idx = dict(index)
    idx["_meta"] = {
        "version": SCAN_INDEX_VERSION,
        "fingerprint": _bundle_fingerprint(bundle),
    }
    path.write_text(
        json.dumps(
            idx,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def refresh_scan_index(cache_skin_dir: Path, bundle: Path) -> Dict[str, Any]:
    from . import bundle_inspector  # local import to avoid circular dependency

    tmp_out = cache_skin_dir / f"__scan__{bundle.stem}"
    tmp_out.mkdir(parents=True, exist_ok=True)
    try:
        index = bundle_inspector.scan_bundle(bundle, tmp_out, export_uss=False)
        tmp_idx_path = tmp_out / "bundle_index.json"
        if tmp_idx_path.exists():
            index = json.loads(tmp_idx_path.read_text(encoding="utf-8"))
        _save_scan_index(cache_skin_dir, bundle, index)
        return index
    finally:
        try:
            for child in tmp_out.iterdir():
                try:
                    child.unlink()
                except Exception as e:
                    log.debug(f"Failed to delete temporary file {child}: {e}")
            tmp_out.rmdir()
        except Exception:
            pass


def load_or_refresh_candidates(
    cache_skin_dir: Path,
    css_dir: Path,
    bundle: Path,
    *,
    refresh: bool,
    css_data: CollectedCss,
    patch_direct: bool,
) -> Optional[Set[str]]:
    index: Optional[Dict[str, Any]] = None
    if not refresh:
        index = load_scan_index(cache_skin_dir, bundle)
    if index is None:
        index = refresh_scan_index(cache_skin_dir, bundle)

    if patch_direct:
        return None

    candidates: Set[str] = set()
    var_map = index.get("var_map", {})
    sel_map = index.get("selector_map", {})

    var_names: Set[str] = set(css_data.global_vars.keys())
    selector_keys: Set[Tuple[str, str]] = set(
        css_data.global_selectors.keys()
    )

    for overrides_list in css_data.asset_map.values():
        for overrides in overrides_list:
            var_names.update(overrides.vars.keys())
            selector_keys.update(overrides.selectors.keys())

    for overrides_list in css_data.files_by_stem.values():
        for overrides in overrides_list:
            var_names.update(overrides.vars.keys())
            selector_keys.update(overrides.selectors.keys())

    for var in var_names:
        if var in var_map:
            for hit in var_map[var]:
                asset = hit.get("asset")
                if asset:
                    candidates.add(asset)

    for selector, prop in selector_keys:
        keys = [selector, selector.lstrip(".")]
        for sel in keys:
            props = sel_map.get(sel)
            if not isinstance(props, dict):
                continue
            if prop in props:
                for hit in props[prop]:
                    asset = hit.get("asset")
                    if asset:
                        candidates.add(asset)
            else:
                for plist in props.values():
                    for hit in plist:
                        asset = hit.get("asset")
                        if asset:
                            candidates.add(asset)

    return candidates if candidates else None


def load_cached_bundle_index(
    css_dir: Path,
    bundle: Path,
    *,
    skin_cache_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Load a cached scan index for *bundle*, falling back to the standard cache layout."""

    cache_root = (
        skin_cache_dir
        if skin_cache_dir is not None
        else cache_dir(root=css_dir.parent.parent) / css_dir.name
    )
    try:
        return load_scan_index(cache_root, bundle)
    except Exception:
        return None
