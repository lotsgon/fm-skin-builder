from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import json
import os
import UnityPy
import gc

from .logger import get_logger
from .css_utils import build_selector_from_parts, serialize_stylesheet_to_uss

log = get_logger(__name__)


def _safe_rule_selectors(data) -> Dict[int, List[str]]:
    rules = getattr(data, "m_Rules", [])
    selectors = getattr(data, "m_ComplexSelectors", []) if hasattr(
        data, "m_ComplexSelectors") else []
    out: Dict[int, List[str]] = {i: [] for i in range(len(rules))}
    for sel in selectors:
        rule_idx = getattr(sel, "ruleIndex", -1)
        if 0 <= rule_idx < len(rules):
            for s in getattr(sel, "m_Selectors", []) or []:
                parts = getattr(s, "m_Parts", [])
                out[rule_idx].append(build_selector_from_parts(parts))
    # fallback names for empty
    for i in range(len(rules)):
        if not out[i]:
            out[i] = [f".rule-{i}", f"rule-{i}"]
    return out


def scan_bundle(bundle_path: Path, out_dir: Path, export_uss: bool = True) -> Dict[str, Any]:
    env = UnityPy.load(str(bundle_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    uss_dir = out_dir / "scan_uss"
    if export_uss:
        uss_dir.mkdir(parents=True, exist_ok=True)

    index: Dict[str, Any] = {
        "bundle": str(bundle_path),
        "assets": [],
        "var_map": {},
        "selector_map": {},
        "conflicts": {"selectors": {}},
        # Additive catalogs for non-style bundles
        "textures": [],
        "sprites": [],
        "aliases": []
    }

    selector_to_assets: Dict[str, set] = {}

    # First pass: collect non-style catalogs (Texture2D, Sprite, AssetBundle aliases)
    for obj in env.objects:
        tname = obj.type.name
        if tname == "Texture2D":
            try:
                data = obj.read()
            except Exception:
                continue
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)
            if name:
                index["textures"].append(str(name))
        elif tname == "Sprite":
            try:
                data = obj.read()
            except Exception:
                continue
            name = getattr(data, "m_Name", None) or getattr(data, "name", None)
            if name:
                index["sprites"].append(str(name))
        elif tname == "SpriteAtlas":
            # Index sprites from SpriteAtlas (for sprite overlay operations)
            try:
                data = obj.read()
            except Exception:
                continue
            packed_names = getattr(data, "m_PackedSpriteNamesToIndex", None)
            if packed_names:
                try:
                    # m_PackedSpriteNamesToIndex is a list of sprite names
                    for sprite_name in list(packed_names):
                        if sprite_name:
                            index["sprites"].append(str(sprite_name))
                except Exception:
                    pass
        elif tname == "AssetBundle":
            try:
                data = obj.read()
            except Exception:
                continue
            container = getattr(data, "m_Container", None)
            if container is None:
                continue
            try:
                for entry in list(container):
                    alias = getattr(entry, "first", None) or getattr(
                        entry, "name", None)
                    if alias:
                        index["aliases"].append(str(alias))
            except Exception:
                pass

    # Second pass: style scanning
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        data = obj.read()
        if not hasattr(data, "colors") or not hasattr(data, "strings"):
            continue
        name = getattr(data, "m_Name", "UnnamedStyleSheet")
        try:
            path_id = getattr(obj, "path_id", None)
        except Exception:
            path_id = None
        strings = list(getattr(data, "strings", []))
        colors = getattr(data, "colors", [])
        rules = getattr(data, "m_Rules", [])
        rule_selectors = _safe_rule_selectors(data)

        asset_info = {
            "name": name,
            "path_id": path_id,
            "string_vars": [s for s in strings if isinstance(s, str) and s.startswith("--")],
            "rules": []
        }

        for i, rule in enumerate(rules):
            selectors = rule_selectors.get(i, [])
            if selectors:
                for sel in selectors:
                    selector_to_assets.setdefault(sel, set()).add(name)
            props_info = []
            for prop in getattr(rule, "m_Properties", []):
                prop_name = getattr(prop, "m_Name", None)
                values_info = []
                for val in getattr(prop, "m_Values", []):
                    vt = getattr(val, "m_ValueType", None)
                    vi = getattr(val, "valueIndex", None)
                    rec: Dict[str, Any] = {"type": vt, "index": vi}
                    if vt in (3, 8, 10) and isinstance(vi, int) and 0 <= vi < len(strings):
                        rec["string"] = strings[vi]
                        if isinstance(strings[vi], str) and strings[vi].startswith("--"):
                            vm = index["var_map"].setdefault(strings[vi], [])
                            vm.append({"asset": name, "rule": i,
                                      "prop": prop_name, "color_index": vi})
                    if vt == 4 and isinstance(vi, int) and 0 <= vi < len(colors):
                        c = colors[vi]
                        rec["color"] = {"r": c.r, "g": c.g, "b": c.b, "a": c.a}
                    values_info.append(rec)
                props_info.append({"name": prop_name, "values": values_info})
                for sel in selectors:
                    sm = index["selector_map"].setdefault(
                        sel, {}).setdefault(prop_name, [])
                    sm.append({"asset": name, "rule": i})
            asset_info["rules"].append(
                {"idx": i, "selectors": selectors, "properties": props_info})

        index["assets"].append(asset_info)

        if export_uss:
            try:
                uss = serialize_stylesheet_to_uss(data)
                (uss_dir / f"{name}.uss").write_text(uss, encoding="utf-8")
            except Exception as e:
                log.warning(f"Could not export USS for {name}: {e}")

    # conflicts: selector defined in multiple assets
    for sel, assets in selector_to_assets.items():
        if len(assets) > 1:
            index["conflicts"]["selectors"][sel] = sorted(list(assets))

    # write index json
    (out_dir / "bundle_index.json").write_text(json.dumps(index,
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    # Proactively release UnityPy env
    try:
        del env
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass
    return index


def scan_target(bundle: Path, out_dir: Path, export_uss: bool = True) -> None:
    if bundle.is_dir():
        for p in sorted(bundle.iterdir()):
            if p.suffix == ".bundle":
                out = out_dir / p.stem
                log.info(f"Scanning bundle: {p}")
                scan_bundle(p, out, export_uss=export_uss)
    else:
        out = out_dir / bundle.stem
        log.info(f"Scanning bundle: {bundle}")
        scan_bundle(bundle, out, export_uss=export_uss)
