from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple, DefaultDict, NamedTuple
from collections import defaultdict
import os
from io import BytesIO

import UnityPy
import gc

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

    def _svg_to_png_bytes(svg_path: Path, width: int = 512, height: int = 512) -> Optional[bytes]:
        """Convert SVG to PNG bytes. Returns None if conversion fails."""
        try:
            # Try cairosvg first (best quality)
            try:
                import cairosvg
                png_bytes = cairosvg.svg2png(
                    url=str(svg_path), output_width=width, output_height=height)
                return png_bytes
            except ImportError:
                pass

            # Fallback to svglib + reportlab
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                from io import BytesIO
                drawing = svg2rlg(svg_path)
                if drawing:
                    # Scale to target size
                    drawing.width = width
                    drawing.height = height
                    drawing.scale(width / drawing.width,
                                  height / drawing.height)
                    buf = BytesIO()
                    renderPM.drawToFile(drawing, buf, fmt="PNG")
                    return buf.getvalue()
            except ImportError:
                pass

            # Fallback to PIL with SVG plugin (requires Pillow with librsvg)
            try:
                from PIL import Image
                img = Image.open(svg_path)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                buf = BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
            except Exception:
                pass

            log.warning(
                f"SVG support not available. Install 'cairosvg' or 'svglib' to use SVG images: {svg_path.name}")
            return None
        except Exception as e:
            log.warning(f"Failed to convert SVG {svg_path.name}: {e}")
            return None

    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        suffix = p.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".svg"}:
            continue
        name = p.stem  # include suffixes like _x2 in the name
        try:
            if suffix == ".svg":
                # Convert SVG to PNG at reasonable default size
                # It will be resized later to match the target sprite size
                png_bytes = _svg_to_png_bytes(p, width=512, height=512)
                if png_bytes:
                    replacements[name] = png_bytes
                    exts[name] = "png"  # Store as PNG after conversion
            else:
                replacements[name] = p.read_bytes()
                exts[name] = suffix.lstrip(".")
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


class SpriteAtlasInfo(NamedTuple):
    """Information about a sprite in an atlas."""
    sprite_name: str
    sprite_index: int
    sprite_path_id: int
    texture_path_id: int
    rect_x: int
    rect_y: int
    rect_width: int
    rect_height: int
    atlas_name: str


def _parse_sprite_atlas(env) -> Dict[str, SpriteAtlasInfo]:
    """Parse SpriteAtlas objects to extract sprite positions using AssetRipper structure.

    Follows the chain:
    1. m_PackedSpriteNamesToIndex: sprite name -> index (list)
    2. m_PackedSprites: index -> Sprite path_id (list)
    3. m_RenderDataMap: indexed by same index -> texture rect and Texture2D path_id (list of tuples)

    Returns dict mapping sprite names to their atlas information.
    """
    sprite_atlas_map: Dict[str, SpriteAtlasInfo] = {}

    for obj in getattr(env, "objects", []):
        tname = getattr(getattr(obj, "type", None), "name", None)
        if tname != "SpriteAtlas":
            continue

        try:
            atlas_data = obj.read()
        except Exception as e:
            log.debug(f"[ATLAS] Failed to read SpriteAtlas: {e}")
            continue

        atlas_name = getattr(atlas_data, "m_Name", None) or getattr(
            atlas_data, "name", None) or "Unknown"

        # Step 1: Parse m_PackedSpriteNamesToIndex (list of sprite names, index = position)
        packed_names = getattr(atlas_data, "m_PackedSpriteNamesToIndex", None)
        if packed_names is None:
            log.debug(f"[ATLAS] No m_PackedSpriteNamesToIndex in {atlas_name}")
            continue

        # Step 2: Parse m_PackedSprites (list of Sprite PPtr, index = position)
        packed_sprites = getattr(atlas_data, "m_PackedSprites", None)
        if packed_sprites is None:
            log.debug(f"[ATLAS] No m_PackedSprites in {atlas_name}")
            continue

        # Step 3: Parse m_RenderDataMap (list of tuples: (key, render_data), index = position)
        render_data_map = getattr(atlas_data, "m_RenderDataMap", None)
        if render_data_map is None:
            log.debug(f"[ATLAS] No m_RenderDataMap in {atlas_name}")
            continue

        try:
            # Convert to lists if needed
            sprite_names_list = list(packed_names)
            sprites_list = list(packed_sprites)
            render_list = list(render_data_map)

            # Verify lengths match
            if not (len(sprite_names_list) == len(sprites_list) == len(render_list)):
                log.warning(
                    f"[ATLAS] Length mismatch in {atlas_name}: names={len(sprite_names_list)}, sprites={len(sprites_list)}, render={len(render_list)}")
                continue

            # Process each sprite by index
            for idx, sprite_name in enumerate(sprite_names_list):
                try:
                    # Get Sprite path_id
                    sprite_ptr = sprites_list[idx]
                    sprite_path_id = getattr(sprite_ptr, "m_PathID", None)
                    if sprite_path_id is None:
                        continue

                    # Handle negative path IDs (convert to unsigned 64-bit)
                    if sprite_path_id < 0:
                        sprite_path_id = sprite_path_id & 0xFFFFFFFFFFFFFFFF

                    # Get render data (tuple of key, value)
                    render_entry = render_list[idx]
                    if isinstance(render_entry, tuple) and len(render_entry) == 2:
                        key, value = render_entry
                    else:
                        continue

                    # Extract textureRect (lowercase in UnityPy)
                    texture_rect = getattr(value, "textureRect", None) or getattr(
                        value, "m_TextureRect", None)
                    if texture_rect is None:
                        continue

                    # Get rectangle coordinates (may be floats)
                    rect_x = getattr(texture_rect, "x", None) or getattr(
                        texture_rect, "m_X", None)
                    rect_y = getattr(texture_rect, "y", None) or getattr(
                        texture_rect, "m_Y", None)
                    rect_width = getattr(texture_rect, "width", None) or getattr(
                        texture_rect, "m_Width", None)
                    rect_height = getattr(texture_rect, "height", None) or getattr(
                        texture_rect, "m_Height", None)

                    if None in (rect_x, rect_y, rect_width, rect_height):
                        continue

                    # Extract texture pointer to get Texture2D path_id (lowercase in UnityPy)
                    texture_ptr = getattr(value, "texture", None) or getattr(
                        value, "m_Texture", None)
                    if texture_ptr is None:
                        continue

                    texture_path_id = getattr(texture_ptr, "m_PathID", None)
                    if texture_path_id is None:
                        continue

                    # Handle negative path IDs
                    if texture_path_id < 0:
                        texture_path_id = texture_path_id & 0xFFFFFFFFFFFFFFFF

                    # Store sprite info (round floats to ints)
                    sprite_atlas_map[str(sprite_name)] = SpriteAtlasInfo(
                        sprite_name=str(sprite_name),
                        sprite_index=idx,
                        sprite_path_id=sprite_path_id,
                        texture_path_id=texture_path_id,
                        rect_x=int(round(rect_x)),
                        rect_y=int(round(rect_y)),
                        rect_width=int(round(rect_width)),
                        rect_height=int(round(rect_height)),
                        atlas_name=atlas_name
                    )
                except Exception as e:
                    log.debug(
                        f"[ATLAS] Failed to parse sprite at index {idx}: {e}")
                    continue

            if sprite_atlas_map:
                log.info(
                    f"[ATLAS] Parsed SpriteAtlas '{atlas_name}' with {len([s for s in sprite_atlas_map.values() if s.atlas_name == atlas_name])} sprites")

        except Exception as e:
            log.debug(f"[ATLAS] Failed to process {atlas_name}: {e}")
            continue

    return sprite_atlas_map


def _swap_textures_in_env(env, replacements: Dict[str, bytes], repl_exts: Optional[Dict[str, str]] = None, name_map: Optional[Dict[str, str]] = None) -> int:
    """Apply replacements to Texture2D assets and sprite atlas overlays in UnityPy env.

    Returns number of textures replaced + sprites overlaid.
    """
    if not replacements:
        return 0

    # Group env textures by base name and scale
    env_by_base: DefaultDict[str, Dict[int, object]] = defaultdict(dict)
    env_exts: DefaultDict[str, Dict[int, Optional[str]]] = defaultdict(dict)
    env_pid_by_base: DefaultDict[str,
                                 Dict[int, Optional[int]]] = defaultdict(dict)
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
        env_pid_by_base[base][scale] = path_id if isinstance(
            path_id, int) else None

    # Collect alias mappings from AssetBundle containers and Sprites to Texture2D path IDs
    alias_entries: List[Tuple[str, int]] = []  # (alias_name, target_path_id)
    sprite_refs_by_pid: Dict[int, int] = {}
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
                sprite_refs_by_pid[pid] = sprite_refs_by_pid.get(pid, 0) + 1

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

    # Build source replacements by base/scale from files
    src_by_base: DefaultDict[str, Dict[int, bytes]] = defaultdict(dict)
    src_ext_by_base: DefaultDict[str,
                                 Dict[int, Optional[str]]] = defaultdict(dict)
    for repl_name, buf in replacements.items():
        sbase, sscale = _parse_base_and_scale(repl_name)
        src_by_base[sbase][sscale] = buf
        if repl_exts is not None:
            src_ext_by_base[sbase][sscale] = repl_exts.get(repl_name)

    # Plan final replacements (target_base/scale -> bytes) considering mapping (target→source only)
    repl_by_base: DefaultDict[str, Dict[int, bytes]] = defaultdict(dict)
    repl_ext_by_base: DefaultDict[str,
                                  Dict[int, Optional[str]]] = defaultdict(dict)
    used_sources: set = set()
    if name_map:
        # Mapping: target_base(±variant) -> source_base
        for tkey, sval in name_map.items():
            if not isinstance(tkey, str) or not isinstance(sval, str):
                continue
            tbase, tscale = _parse_base_and_scale(tkey)
            sbase, _ = _parse_base_and_scale(sval)
            s_scales = src_by_base.get(sbase)
            if not s_scales:
                continue
            if tscale != 1:
                if tscale in s_scales:
                    repl_by_base[tbase][tscale] = s_scales[tscale]
                    if repl_exts is not None and tscale in src_ext_by_base.get(sbase, {}):
                        repl_ext_by_base[tbase][tscale] = src_ext_by_base[sbase][tscale]
                    used_sources.add((sbase, tscale))
                else:
                    log.warning(
                        f"[TEXTURE] Mapping for '{tkey}' requested {tscale}x but no replacement scale found for source '{sbase}'.")
            else:
                for sscale, buf in s_scales.items():
                    repl_by_base[tbase][sscale] = buf
                    if repl_exts is not None and sscale in src_ext_by_base.get(sbase, {}):
                        repl_ext_by_base[tbase][sscale] = src_ext_by_base[sbase][sscale]
                    used_sources.add((sbase, sscale))

    # Identity mapping for any sources not covered by mapping
    for sbase, scale_map in src_by_base.items():
        for sscale, buf in scale_map.items():
            if (sbase, sscale) in used_sources:
                continue
            repl_by_base[sbase][sscale] = buf
            if repl_exts is not None and sscale in src_ext_by_base.get(sbase, {}):
                repl_ext_by_base[sbase][sscale] = src_ext_by_base[sbase][sscale]

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
            # Block atlas replacements: if this texture appears to be shared by multiple Sprites
            pid = env_pid_by_base.get(base, {}).get(scale)
            if isinstance(pid, int) and sprite_refs_by_pid.get(pid, 0) > 1:
                log.error(
                    f"[TEXTURE] Replacement blocked: target '{base}' at {scale}x is shared by {sprite_refs_by_pid[pid]} sprites (atlas). Atlas replacement is not supported yet.")
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
                    # Size validation (warn on mismatch)
                    tgt_w = getattr(data, "m_Width", None) or getattr(
                        data, "width", None)
                    tgt_h = getattr(data, "m_Height", None) or getattr(
                        data, "height", None)
                    if isinstance(tgt_w, int) and isinstance(tgt_h, int):
                        try:
                            rw, rh = img.size
                            if (rw, rh) != (tgt_w, tgt_h):
                                log.warning(
                                    f"[TEXTURE] Size mismatch for '{base}' at {scale}x: bundle is {tgt_w}x{tgt_h}, replacement is {rw}x{rh}. Proceeding to replace."
                                )
                        except Exception:
                            pass
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

    # Parse SpriteAtlas for sprite overlay operations
    sprite_atlas_map = _parse_sprite_atlas(env)

    # Track vector sprite replacements (processed separately)
    vector_sprite_replacements: Dict[str, dict] = {}

    # Separate vector sprites from texture sprites in name_map
    texture_name_map: Dict[str, str] = {}
    if name_map:
        for key, value in name_map.items():
            if isinstance(value, dict) and value.get("type") == "vector":
                vector_sprite_replacements[key] = value
            elif isinstance(value, str):
                texture_name_map[key] = value

    # Perform sprite atlas overlays
    sprite_overlays = 0
    if sprite_atlas_map and texture_name_map:
        # Expand wildcard patterns and scale-agnostic mappings
        import fnmatch
        expanded_name_map: Dict[str, str] = {}

        for pattern, source_name in texture_name_map.items():
            # Check if pattern has wildcard
            if '*' in pattern or '?' in pattern:
                # Match against all sprites in atlas
                matched_count = 0
                for sprite_name in sprite_atlas_map.keys():
                    if fnmatch.fnmatch(sprite_name, pattern):
                        expanded_name_map[sprite_name] = source_name
                        matched_count += 1
                if matched_count > 0:
                    log.info(
                        f"[ATLAS] Pattern '{pattern}' matched {matched_count} sprites")
                else:
                    log.debug(
                        f"[ATLAS] Pattern '{pattern}' matched no sprites")
            else:
                # Try exact match first
                if pattern in sprite_atlas_map:
                    expanded_name_map[pattern] = source_name
                else:
                    # Try scale-agnostic matching: add _1x, _2x, _3x, _4x suffixes
                    matched_count = 0
                    for scale in ['1x', '2x', '3x', '4x']:
                        scaled_name = f"{pattern}_{scale}"
                        if scaled_name in sprite_atlas_map:
                            expanded_name_map[scaled_name] = source_name
                            matched_count += 1

                    if matched_count == 0:
                        log.debug(
                            f"[ATLAS] Sprite '{pattern}' not found (tried exact and _1x/_2x/_3x/_4x variants)")

        # Use expanded map for processing
        name_map = expanded_name_map

        try:
            from PIL import Image  # type: ignore

            # Build texture_path_id to texture data mapping
            tex_by_pathid_full: Dict[int, object] = {}
            for obj in getattr(env, "objects", []):
                if getattr(getattr(obj, "type", None), "name", None) != "Texture2D":
                    continue
                try:
                    data = obj.read()
                    path_id = getattr(obj, "path_id", None)
                    if path_id is not None:
                        # Handle negative path IDs
                        if path_id < 0:
                            path_id = path_id & 0xFFFFFFFFFFFFFFFF
                        tex_by_pathid_full[path_id] = data
                except Exception:
                    continue

            # Track modified atlas textures
            modified_atlases: Dict[int,
                                   Tuple[object, Image.Image, int, int]] = {}

            # Process each mapping entry (only texture sprites, vector sprites handled separately)
            for target_sprite_name, source_image_name in name_map.items():

                # Check if target exists in sprite atlas
                atlas_info = sprite_atlas_map.get(target_sprite_name)
                if atlas_info is None:
                    continue

                # Check if source image exists
                source_base, source_scale = _parse_base_and_scale(
                    source_image_name)
                source_buf = src_by_base.get(source_base, {}).get(source_scale)
                if source_buf is None:
                    log.warning(
                        f"[ATLAS] Source image '{source_image_name}' not found for sprite '{target_sprite_name}'")
                    continue

                # Get or load the atlas texture
                texture_path_id = atlas_info.texture_path_id
                if texture_path_id not in modified_atlases:
                    atlas_tex = tex_by_pathid_full.get(texture_path_id)
                    if atlas_tex is None:
                        log.warning(
                            f"[ATLAS] Atlas texture with path_id {texture_path_id} not found for sprite '{target_sprite_name}'")
                        continue

                    try:
                        atlas_img = atlas_tex.image.convert("RGBA")
                        atlas_width = getattr(atlas_tex, "m_Width", None) or getattr(
                            atlas_tex, "width", None) or atlas_img.width
                        atlas_height = getattr(atlas_tex, "m_Height", None) or getattr(
                            atlas_tex, "height", None) or atlas_img.height
                        modified_atlases[texture_path_id] = (
                            atlas_tex, atlas_img, atlas_width, atlas_height)
                    except Exception as e:
                        log.warning(
                            f"[ATLAS] Failed to load atlas texture: {e}")
                        continue

                atlas_tex, atlas_img, atlas_width, atlas_height = modified_atlases[
                    texture_path_id]

                # Load source image
                try:
                    source_img = Image.open(
                        BytesIO(source_buf)).convert("RGBA")
                except Exception as e:
                    log.warning(
                        f"[ATLAS] Failed to load source image '{source_image_name}': {e}")
                    continue

                # Calculate position (Unity uses bottom-left origin, PIL uses top-left)
                rect_x = atlas_info.rect_x
                rect_y = atlas_info.rect_y
                rect_width = atlas_info.rect_width
                rect_height = atlas_info.rect_height

                # Convert from Unity bottom-left to PIL top-left coordinates
                pil_top = atlas_height - (rect_y + rect_height)
                pil_left = rect_x

                # Resize source image to match the sprite's rectangle size
                if (source_img.width, source_img.height) != (rect_width, rect_height):
                    source_img = source_img.resize(
                        (rect_width, rect_height), Image.Resampling.LANCZOS)

                # Clear the original sprite region (to avoid artifacts)
                clear_box = (pil_left, pil_top, pil_left +
                             rect_width, pil_top + rect_height)
                atlas_img.paste(
                    Image.new("RGBA", (rect_width, rect_height), (0, 0, 0, 0)), clear_box)

                # Paste the new sprite with alpha channel
                paste_box = (pil_left, pil_top)
                atlas_img.paste(source_img, paste_box, source_img)

                # DEBUG: Verify the paste worked
                crop_check = atlas_img.crop(
                    (pil_left, pil_top, pil_left + rect_width, pil_top + rect_height))
                crop_extrema = crop_check.getextrema()
                log.info(
                    f"[ATLAS] DEBUG: After paste at PIL coords ({pil_left}, {pil_top}), region pixel extrema: {crop_extrema}")

                modified_atlases[texture_path_id] = (
                    atlas_tex, atlas_img, atlas_width, atlas_height)
                sprite_overlays += 1

                log.info(
                    f"[ATLAS] Overlaid sprite '{target_sprite_name}' with '{source_image_name}' at ({rect_x}, {rect_y}) size {rect_width}x{rect_height} in atlas '{atlas_info.atlas_name}'")

            # Save modified atlas textures back
            for texture_path_id, (atlas_tex, atlas_img, tw, th) in modified_atlases.items():
                try:
                    tex_name = getattr(atlas_tex, "m_Name", None) or getattr(
                        atlas_tex, "name", None) or f"texture_{texture_path_id}"
                    log.info(
                        f"[ATLAS] Saving modified atlas texture '{tex_name}' (path_id={texture_path_id})")

                    # CRITICAL: Clear m_StreamData so Unity uses image_data instead of external resource
                    if hasattr(atlas_tex, "m_StreamData"):
                        # Set StreamData to empty/zero values so it doesn't reference external compressed data
                        atlas_tex.m_StreamData.offset = 0
                        atlas_tex.m_StreamData.size = 0
                        atlas_tex.m_StreamData.path = ""
                        log.info(
                            f"[ATLAS] DEBUG: Cleared m_StreamData for '{tex_name}'")

                    if hasattr(atlas_tex, "set_image"):
                        atlas_tex.set_image(atlas_img)
                        log.info(
                            f"[ATLAS] DEBUG: Used set_image() for '{tex_name}'")
                    elif hasattr(atlas_tex, "image_data"):
                        buf_io = BytesIO()
                        atlas_img.save(buf_io, format="PNG")
                        atlas_tex.image_data = buf_io.getvalue()
                        log.info(
                            f"[ATLAS] DEBUG: Used image_data for '{tex_name}'")
                    else:
                        log.warning(
                            f"[ATLAS] No save method available for '{tex_name}'")

                    if hasattr(atlas_tex, "save"):
                        try:
                            atlas_tex.save()
                            log.info(
                                f"[ATLAS] DEBUG: Called save() on '{tex_name}'")
                        except Exception as e:
                            log.warning(
                                f"[ATLAS] save() failed for '{tex_name}': {e}")
                except Exception as e:
                    log.warning(
                        f"[ATLAS] Failed to save modified atlas texture: {e}")

            # CRITICAL: Update individual Sprite objects to reflect the modified atlas
            # Sprites cache their texture data and the game reads from this cache, not the atlas directly
            sprites_updated = 0
            for sprite_name in name_map.keys():
                atlas_info = sprite_atlas_map.get(sprite_name)
                if atlas_info is None:
                    continue

                # Find the Sprite object by path_id
                sprite_path_id = atlas_info.sprite_path_id
                for obj in getattr(env, "objects", []):
                    if getattr(getattr(obj, "type", None), "name", None) != "Sprite":
                        continue
                    if getattr(obj, "path_id", None) != sprite_path_id:
                        continue

                    try:
                        sprite_obj = obj.read()

                        # Force sprite to regenerate its cached image from the modified atlas
                        # by clearing any cached data and calling save
                        if hasattr(sprite_obj, "save"):
                            sprite_obj.save()
                            sprites_updated += 1
                            log.debug(
                                f"[ATLAS] Updated Sprite object '{sprite_name}'")
                    except Exception as e:
                        log.debug(
                            f"[ATLAS] Failed to update Sprite '{sprite_name}': {e}")

            if sprites_updated > 0:
                log.info(
                    f"[ATLAS] Updated {sprites_updated} Sprite objects to reflect atlas changes")

        except ImportError:
            log.warning(
                "[ATLAS] PIL not available, sprite atlas overlays skipped")
        except Exception as e:
            log.warning(f"[ATLAS] Sprite atlas overlay failed: {e}")

    # Process vector sprite replacements (for Sprite objects with mesh data, no texture)
    vectors_replaced = 0
    if vector_sprite_replacements:
        try:
            from .vector_sprites import replace_vector_sprite

            # Expand scale-agnostic patterns for vector sprites
            expanded_vector_map: Dict[str, dict] = {}
            for target_name, vector_config in vector_sprite_replacements.items():
                # Check if target already has scale suffix
                if any(target_name.endswith(f"_{scale}") for scale in ["1x", "2x", "3x", "4x"]):
                    expanded_vector_map[target_name] = vector_config
                else:
                    # Expand to all scales
                    for scale in ["1x", "2x", "3x", "4x"]:
                        expanded_vector_map[f"{target_name}_{scale}"] = vector_config

            # Find and process Sprite objects
            for obj in env.objects:
                if obj.type.name != "Sprite":
                    continue

                sprite_obj = obj.read()
                sprite_name = getattr(sprite_obj, "m_Name", None) or getattr(
                    sprite_obj, "name", None)

                if not sprite_name or sprite_name not in expanded_vector_map:
                    continue

                # Check if this is actually a vector sprite (no texture reference)
                rd = sprite_obj.m_RD
                if rd.texture.m_FileID != 0 or rd.texture.m_PathID != 0:
                    log.debug(
                        f"[VECTOR] Skipping '{sprite_name}' - has texture reference (not a vector sprite)")
                    continue

                # Get vector configuration
                vector_config = expanded_vector_map[sprite_name]
                shape = vector_config.get("shape", "circle")
                color = vector_config.get("color", [255, 255, 255, 255])

                # Extract shape-specific parameters
                kwargs = {k: v for k, v in vector_config.items() if k not in [
                    "type", "shape", "color"]}

                try:
                    replace_vector_sprite(sprite_obj, shape, color, **kwargs)
                    vectors_replaced += 1
                    log.info(
                        f"[VECTOR] Replaced '{sprite_name}' with {shape} (color={color})")
                except Exception as e:
                    log.warning(
                        f"[VECTOR] Failed to replace '{sprite_name}': {e}")

        except ImportError as e:
            log.warning(f"[VECTOR] Vector sprite module not available: {e}")
        except Exception as e:
            log.warning(f"[VECTOR] Vector sprite replacement failed: {e}")

    if replaced == 0 and sprite_overlays == 0 and vectors_replaced == 0:
        # Help users discover names when no matches occurred
        sample = sorted(env_by_base.keys())[:10]
        if sample:
            log.info(
                f"[TEXTURE] No matches. Candidate names include: {sample} ...")
        # If bundle has Sprites but their referenced textures aren't present in this bundle, hint about cross-bundle textures
        missing_refs = []
        for alias_name, pid in alias_entries:
            if isinstance(pid, int) and pid not in tex_by_pathid:
                missing_refs.append(alias_name)
        if missing_refs:
            log.info("[TEXTURE] This bundle contains Sprites/aliases whose Texture2D data is in another bundle. Try patching the bundle that actually contains the textures (often '*_assets_common.bundle').")

    return replaced + sprite_overlays + vectors_replaced


class TextureSwapResult(NamedTuple):
    replaced_count: int
    out_file: Optional[Path]


def swap_textures(
    bundle_path: Path,
    skin_dir: Path,
    includes: List[str],
    out_dir: Path,
    dry_run: bool = False,
) -> TextureSwapResult:
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

    # Optional name mapping files. Precedence: global assets/mapping.json, then type-specific mapping (icons/backgrounds) overrides.
    name_map: Dict[str, str] = {}

    def _load_map_file(p: Path) -> None:
        nonlocal name_map
        if not p.exists():
            return
        try:
            import json
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if isinstance(k, str):
                        # Accept both string values (texture sprites) and dict values (vector sprites)
                        if isinstance(v, str):
                            k_noext, _ = _strip_image_extension(k)
                            name_map[k_noext] = v
                        elif isinstance(v, dict):
                            k_noext, _ = _strip_image_extension(k)
                            name_map[k_noext] = v
            else:
                log.warning(f"[TEXTURE] mapping file is not an object: {p}")
        except Exception as e:
            log.warning(f"[TEXTURE] Failed to read mapping file {p}: {e}")

    for fname in ("mapping.json", "map.json"):
        _load_map_file(skin_dir / "assets" / fname)
    # Type-specific mapping overrides global
    for sub in ("icons", "backgrounds"):
        for fname in ("mapping.json", "map.json"):
            _load_map_file(skin_dir / "assets" / sub / fname)

    # Check if there are vector sprite replacements (don't need texture files)
    has_vector_sprites = any(isinstance(v, dict) and v.get(
        "type") == "vector" for v in name_map.values())

    if not replacements and not has_vector_sprites:
        return TextureSwapResult(0, None)

    env = UnityPy.load(str(bundle_path))
    count = _swap_textures_in_env(
        env, replacements, repl_exts, name_map or None)
    if count == 0:
        # Cleanup UnityPy env before returning
        try:
            del env
        except Exception:
            pass
        try:
            gc.collect()
        except Exception:
            pass
        return TextureSwapResult(0, None)
    if dry_run:
        log.info(
            f"[DRY-RUN] Would modify {count} textures/sprites in {bundle_path.name}")
        # Cleanup UnityPy env before returning
        try:
            del env
        except Exception:
            pass
        try:
            gc.collect()
        except Exception:
            pass
        return TextureSwapResult(count, None)

    out_dir.mkdir(parents=True, exist_ok=True)
    name, ext = os.path.splitext(bundle_path.name)
    out_file = out_dir / f"{name}_modified{ext}"
    with open(out_file, "wb") as f:
        f.write(env.file.save())
    log.info(f"💾 Saved texture-swapped bundle → {out_file}")
    # Cleanup UnityPy env after saving
    try:
        del env
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass
    return TextureSwapResult(count, out_file)
