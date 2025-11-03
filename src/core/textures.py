from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple, DefaultDict
from collections import defaultdict
import os
from io import BytesIO

import UnityPy

from .logger import get_logger

log = get_logger(__name__)


def _collect_image_bytes(root: Path) -> Tuple[Dict[str, bytes], Dict[str, str]]:
    """Collect replacement images under a root folder (e.g., assets/icons or assets/backgrounds).

    Returns map of asset_name (filename without extension) -> bytes.
    The name includes any variant suffix (e.g., Icon_x2) so exact matches work.
    """
    replacements: Dict[str, bytes] = {}
    exts: Dict[str, str] = {}
    if not root.exists():
        return replacements, exts
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        name = p.stem  # include suffixes like _x2 in the name
        try:
            replacements[name] = p.read_bytes()
            exts[name] = p.suffix.lower().lstrip(".")
        except Exception as e:
            log.warning(f"Failed to read image {p}: {e}")
    return replacements, exts


def _strip_image_extension(name: str) -> Tuple[str, Optional[str]]:
    n = name
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        if n.endswith(ext):
            return n[: -len(ext)], ext.lower().lstrip('.')
    return n, None


def _parse_base_and_scale(name: str) -> Tuple[str, int]:
    """Return (base_name, scale) parsed from common variant suffixes.

    Supports:
    - Name_x1, Name_x2, Name_x4
    - Name@2x, Name@4x
    Defaults to scale=1 when no suffix present.
    """
    import re

    # Strip known image extension first so env names like 'Foo_x2.png' match 'Foo_x2'
    name_no_ext, _ = _strip_image_extension(name)
    m = re.match(r"^(.*)_x(\d+)$", name_no_ext)
    if m:
        base, s = m.group(1), int(m.group(2))
        return base, s if s > 0 else 1
    m = re.match(r"^(.*)@(\d+)x$", name_no_ext)
    if m:
        base, s = m.group(1), int(m.group(2))
        return base, s if s > 0 else 1
    return name_no_ext, 1


def _swap_textures_in_env(env, replacements: Dict[str, bytes], repl_exts: Optional[Dict[str, str]] = None) -> int:
    """Apply replacements to Texture2D assets in UnityPy env with variant awareness.

    Returns number of textures replaced.
    """
    if not replacements:
        return 0

    # Group env textures by base name and scale
    env_by_base: DefaultDict[str, Dict[int, object]] = defaultdict(dict)
    env_exts: DefaultDict[str, Dict[int, Optional[str]]] = defaultdict(dict)
    tex_by_pathid: Dict[int, Tuple[str, int, object]] = {}
    for obj in getattr(env, "objects", []):
        if getattr(getattr(obj, "type", None), "name", None) != "Texture2D":
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        raw_name = getattr(data, "m_Name", None) or getattr(data, "name", None)
        if not raw_name:
            continue
        # Track extension from raw name (if present)
        _name_no_ext, env_ext = _strip_image_extension(raw_name)
        base, scale = _parse_base_and_scale(raw_name)
        env_by_base[base][scale] = data
        env_exts[base][scale] = env_ext
        # Map by path_id for alias lookup (from AssetBundle/Sprite)
        path_id = getattr(obj, "path_id", None)
        if isinstance(path_id, int):
            tex_by_pathid[path_id] = (base, scale, data)

    # Collect alias mappings from AssetBundle containers and Sprites to Texture2D path IDs
    alias_entries: List[Tuple[str, int]] = []  # (alias_name, target_path_id)
    for obj in getattr(env, "objects", []):
        tname = getattr(getattr(obj, "type", None), "name", None)
        if tname == "AssetBundle":
            try:
                data = obj.read()
            except Exception:
                continue
            container = getattr(data, "m_Container", None)
            if container is None:
                continue
            try:
                # UnityPy often exposes m_Container as a list of entries
                for entry in list(container):
                    # Try common shapes: entry.first (name) + entry.second (PPtr), or entry.name + entry.asset
                    alias = getattr(entry, "first", None) or getattr(
                        entry, "name", None)
                    asset = getattr(entry, "second", None) or getattr(
                        entry, "asset", None)
                    if alias and asset is not None:
                        pid = getattr(asset, "m_PathID", None)
                        if isinstance(pid, int):
                            alias_entries.append((str(alias), pid))
            except Exception:
                pass
        elif tname == "Sprite":
            try:
                data = obj.read()
            except Exception:
                continue
            alias = getattr(data, "m_Name", None) or getattr(
                data, "name", None)
            if not alias:
                continue
            pid = None
            try:
                # Common location of texture PPtr in UnityPy Sprite
                rd = getattr(data, "m_RD", None)
                tex_ptr = getattr(
                    rd, "texture", None) if rd is not None else None
                pid = getattr(tex_ptr, "m_PathID",
                              None) if tex_ptr is not None else None
                if pid is None:
                    tex_ptr = getattr(data, "m_Texture", None)
                    pid = getattr(tex_ptr, "m_PathID",
                                  None) if tex_ptr is not None else None
            except Exception:
                pid = None
            if isinstance(pid, int):
                alias_entries.append((str(alias), pid))

    # Register aliases as additional base/scale keys pointing to the same Texture2D data
    for alias_name, pid in alias_entries:
        base, scale = _parse_base_and_scale(alias_name)
        if pid in tex_by_pathid:
            _orig_base, _orig_scale, data = tex_by_pathid[pid]
            if scale not in env_by_base.get(base, {}):
                env_by_base[base][scale] = data
                # Try to infer extension from alias name, else reuse original
                _noext, env_ext = _strip_image_extension(alias_name)
                if env_ext is None:
                    env_ext = env_exts.get(_orig_base, {}).get(_orig_scale)
                env_exts[base][scale] = env_ext

    # Group replacements by base name and scale
    repl_by_base: DefaultDict[str, Dict[int, bytes]] = defaultdict(dict)
    repl_ext_by_base: DefaultDict[str,
                                  Dict[int, Optional[str]]] = defaultdict(dict)
    for repl_name, buf in replacements.items():
        base, scale = _parse_base_and_scale(repl_name)
        repl_by_base[base][scale] = buf
        if repl_exts is not None:
            repl_ext_by_base[base][scale] = repl_exts.get(repl_name)

    # Warn about variant coverage
    for base, variants in env_by_base.items():
        env_scales = sorted(variants.keys())
        repl_scales = sorted(repl_by_base.get(base, {}).keys())
        if len(env_scales) > 1:
            if not repl_scales:
                continue
            missing = [s for s in env_scales if s not in repl_scales]
            if missing:
                log.warning(
                    f"[TEXTURE] Only {len(repl_scales)}/{len(env_scales)} variants provided for '{base}' "
                    f"(provided: {repl_scales}, missing: {missing}). Visual quality may be affected on high-DPI."
                )

    # Apply replacements where scale matches exactly
    replaced = 0
    for base, scale_map in repl_by_base.items():
        env_scale_map = env_by_base.get(base, {})
        if not env_scale_map:
            # No targets for this base
            continue
        for scale, buf in scale_map.items():
            data = env_scale_map.get(scale)
            if data is None:
                # Replacement exists for variant that bundle doesn't have
                log.debug(
                    f"[TEXTURE] No matching asset variant for '{base}' at {scale}x; ignoring replacement.")
                continue
            try:
                # Prefer PIL path for set_image when available
                used_pil = False
                try:
                    from PIL import Image  # type: ignore
                    used_pil = True
                except Exception:
                    used_pil = False

                if used_pil and hasattr(data, "set_image"):
                    from PIL import Image  # type: ignore
                    img = Image.open(BytesIO(buf))
                    data.set_image(img)
                elif hasattr(data, "image_data"):
                    data.image_data = buf
                else:
                    setattr(data, "_replaced_bytes", buf)  # test fallback
                # Warn about format mismatch (e.g., PNG -> JPG)
                if repl_exts is not None:
                    src_ext = repl_ext_by_base.get(base, {}).get(scale)
                    tgt_ext = env_exts.get(base, {}).get(scale)
                    if src_ext and tgt_ext and src_ext.lower() != tgt_ext.lower():
                        log.warning(
                            f"[TEXTURE] Format mismatch for '{base}' at {scale}x: bundle is {tgt_ext.upper()}, replacement is {src_ext.upper()}. Proceeding to replace."
                        )
                if hasattr(data, "save"):
                    try:
                        data.save()
                    except Exception:
                        pass
                name_display = f"{base}{'' if scale == 1 else f'_x{scale}'}"
                log.info(
                    f"  [TEXTURE] Replaced '{name_display}' ({len(buf)} bytes)")
                replaced += 1
            except Exception as e:
                log.warning(
                    f"  [TEXTURE] Failed to replace texture '{base}' at {scale}x: {e}")

    if replaced == 0:
        # Help users discover names when no matches occurred
        sample = sorted(env_by_base.keys())[:10]
        if sample:
            log.info(
                f"[TEXTURE] No matches. Candidate names include: {sample} ...")
    return replaced


def swap_textures(
    bundle_path: Path,
    skin_dir: Path,
    includes: List[str],
    out_dir: Path,
    dry_run: bool = False,
) -> Optional[Path]:
    """Swap textures in bundle based on skin assets folders.

    - icons from skins/<skin>/assets/icons
    - backgrounds from skins/<skin>/assets/backgrounds

    Returns output bundle path if a write occurred; None otherwise.
    """
    icon_dir = skin_dir / "assets" / "icons"
    bg_dir = skin_dir / "assets" / "backgrounds"

    replacements: Dict[str, bytes] = {}
    repl_exts: Dict[str, str] = {}
    if "assets/icons" in includes and icon_dir.exists():
        r, e = _collect_image_bytes(icon_dir)
        replacements.update(r)
        repl_exts.update(e)
    if "assets/backgrounds" in includes and bg_dir.exists():
        r, e = _collect_image_bytes(bg_dir)
        replacements.update(r)
        repl_exts.update(e)

    if not replacements:
        return None

    env = UnityPy.load(str(bundle_path))
    count = _swap_textures_in_env(env, replacements, repl_exts)
    if count == 0:
        return None
    if dry_run:
        log.info(
            f"[DRY-RUN] Would replace {count} textures in {bundle_path.name}")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    name, ext = os.path.splitext(bundle_path.name)
    out_file = out_dir / f"{name}_modified{ext}"
    with open(out_file, "wb") as f:
        f.write(env.file.save())
    log.info(f"💾 Saved texture-swapped bundle → {out_file}")
    return out_file
