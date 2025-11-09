from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
import fnmatch

DEFAULT_TEXTURE_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".svg"}

__all__ = [
    "collect_replacement_stems",
    "load_texture_name_map",
    "gather_texture_names_from_index",
    "should_swap_textures",
]


def collect_replacement_stems(root: Path, *, extensions: Optional[Iterable[str]] = None) -> List[str]:
    """Return filename stems for replacement assets under *root*."""
    exts = {e.lower() for e in (extensions or DEFAULT_TEXTURE_EXTENSIONS)}
    stems: List[str] = []
    if not root.exists():
        return stems
    for path in root.glob("*.*"):
        if path.suffix.lower() in exts:
            stems.append(path.stem)
    return stems


def load_texture_name_map(skin_root: Path) -> Dict[str, str]:
    """Load mapping.json files that map replacement stems to target texture names."""
    name_map: Dict[str, str] = {}

    def _load_json(path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(key, str) and isinstance(value, str):
                    name_map[key] = value

    assets_dir = skin_root / "assets"
    for fname in ("mapping.json", "map.json"):
        _load_json(assets_dir / fname)
    for subdir in ("icons", "backgrounds"):
        sub_assets = assets_dir / subdir
        for fname in ("mapping.json", "map.json"):
            _load_json(sub_assets / fname)

    return name_map


def gather_texture_names_from_index(index: Optional[Dict[str, object]]) -> Set[str]:
    """Extract texture-like asset names from a scan index."""

    if not isinstance(index, dict):
        return set()

    names: Set[str] = set()
    for key in ("textures", "aliases", "sprites"):
        values = index.get(key)
        if isinstance(values, list):
            for entry in values:
                try:
                    names.add(str(entry))
                except Exception:
                    continue
    return names


def should_swap_textures(
    *,
    bundle_name: str,
    texture_names: Set[str],
    target_names: Set[str],
    replace_stems: Set[str],
    want_icons: bool,
    want_backgrounds: bool,
) -> bool:
    """Return True when texture swapping should occur for the given bundle."""

    bundle_name_lower = bundle_name.lower()
    if texture_names:
        if target_names & texture_names:
            return True

        lowered = {name.lower() for name in texture_names}
        for target in target_names:
            target_lower = target.lower()
            # Check for exact match
            if target_lower in lowered:
                return True
            # Only use fnmatch if the target contains wildcards
            if any(wildcard in target_lower for wildcard in ("*", "?", "[")):
                if any(fnmatch.fnmatch(name, target_lower) for name in lowered):
                    return True
            # Check for prefix match or exact match with underscore
            if any(
                name.startswith(f"{target_lower}_") or name == target_lower
                for name in lowered
            ):
                return True

        if any(stem.lower() in lowered for stem in replace_stems):
            return True
    else:
        if want_icons and "icon" in bundle_name_lower:
            return True
        if want_backgrounds and "background" in bundle_name_lower:
            return True

    return False
