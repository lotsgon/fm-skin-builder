# 🧩 Football Manager Icon Replacement Context (for Copilot)

## 🎯 Goal
Extend the existing Python-based Unity bundle patcher to correctly replace **icon sprites** used by `SIImage` components in *Football Manager 2026*.
Current logic updates `Texture2D` data within atlas bundles successfully, but **some icons (e.g. rating stars)** don’t update in-game because their `Sprite` assets live in **separate bundles**.

The task is to update or create code that correctly handles this multi-bundle icon setup.

---

## 🧠 Problem Summary

Football Manager’s Unity asset structure for icons works like this:

| Bundle Type | Typical Name | Contains | Notes |
|--------------|---------------|----------|-------|
| **Atlas bundle** | `FMImages_4x.bundle` (and `_1x`, `_2x`, etc.) | `Texture2D` (atlas PNG), `SpriteAtlas` | Holds the physical texture sheet |
| **Sprite bundle** | `FMImages_Sprites_4x.bundle` (and variants) | Individual `Sprite` assets (`star_full`, `star_half`, etc.) | Each sprite references the atlas texture by file/path ID |

When patching:
- The tool currently replaces the `Texture2D` data in the atlas bundle.
- However, the `Sprite` assets in the other bundle **still reference the old texture**, so `SIImage` continues showing the original sprite.
- `SIImage` doesn’t resolve via stylesheet; it calls `SpriteManager.Get()` to fetch a specific `Sprite` object by name.

Therefore, we must **patch or rebuild** the `Sprite` assets so their `texture` reference points to the replaced atlas texture.

---

## ⚙️ Required Behaviour

1. **Detect related bundles**
   - Identify atlas bundles (`FMImages_*.bundle`) and sprite bundles (`FMImages_Sprites_*.bundle`) that share a size suffix (`_1x`, `_2x`, `_4x`).
   - Pair them for processing.

2. **Locate assets**
   - In the atlas bundle: find the `Texture2D` (usually named `sactx-3-...FMImages_4x...png`) and the `SpriteAtlas`.
   - In the sprite bundle: iterate over all `Sprite` objects (e.g. `star_full`, `star_half`, etc.).

3. **Patch references**
   - For each `Sprite` in the sprite bundle:
     - Check if its `m_RD.texture` or `m_Texture` points to a different texture (wrong `PathID` / `FileID`).
     - Replace that reference with the updated `Texture2D` from the atlas bundle.
     - Optionally filter only names containing `star`, `rating`, or any icon overrides we’re editing.

4. **Save updated bundles**
   - Output to a new directory (e.g. `output/FMImages_Sprites_4x.bundle`).
   - Preserve dependency metadata so the Sprite bundle still depends on the atlas bundle.

---

## 🧰 Suggested Implementation (UnityPy-based)

```python
import UnityPy
from pathlib import Path

def patch_sprite_texture(sprites_path, atlas_path, filter_keywords=("star",)):
    sprites_env = UnityPy.load(sprites_path)
    atlas_env   = UnityPy.load(atlas_path)

    # Locate new texture
    new_texture_obj = next(
        (o for o in atlas_env.objects if o.type.name == "Texture2D"), None
    )
    if not new_texture_obj:
        print(f"No Texture2D found in {atlas_path}")
        return

    replaced = 0
    for obj in sprites_env.objects:
        if obj.type.name != "Sprite":
            continue
        data = obj.read()
        if any(k.lower() in data.name.lower() for k in filter_keywords):
            data.texture = new_texture_obj.read()
            obj.save(data)
            replaced += 1

    out_path = Path("output") / Path(sprites_path).name
    sprites_env.save(out_path)
    print(f"✅ Patched {replaced} sprites → {out_path}")
```

# Example usage:
# patch_sprite_texture("FMImages_Sprites_4x.bundle", "FMImages_4x.bundle")


## ⚠️ Implementation Notes
- Sprite rects (m_RD.rect) must not change — only texture reference updates.

- Keep the same suffixes (_1x/_2x/_4x) for correct runtime resolution.

- If FM caches sprites in memory, ensure cache-clearing between runs (game restart or force asset reload).

- Similar logic could be reused for other runtime-driven SIImage assets beyond rating stars.

##  🧩 Future Extension (Optional)
Add detection for SITextureImage textures (club kits) and replace base recolourable templates.

Automatically scan all Sprite bundles for cross-bundle texture dependencies and repair them.

## 🪪 Context References
Unity Sprite serialization fields: m_RD.texture, m_Texture, m_Name, m_Rect

FM26 UI runtime uses SpriteManager.Get(string name) and SIImage.SetSprite()

Only bundle-level patching is permitted (no code injection)

## ✅ Copilot’s Goals
Modify or extend existing patcher code so that sprites in separate bundles correctly reference the newly replaced atlas texture, fixing icon replacement for SIImage elements such as rating stars.

## 🆕 Vector Sprite Overrides

Vector-only sprites (no Texture2D reference) can now be driven directly from mapping files. Add an entry such as:

```json
{
    "ability=minimum, potential level=full, youth=true": {
        "type": "vector",
        "svg_file": "assets/icons/vector/ability_minimum.svg",
        "color": "#ffd700",
        "scale": 0.62
    }
}
```

When the sprite bundle is processed, the SVG file is parsed into mesh data and the colour is normalised to RGBA (0-255). Provide `_1x`/`_2x` suffixes if you need different artwork per scale, otherwise the mapping fans out automatically for the standard DPI variants.
