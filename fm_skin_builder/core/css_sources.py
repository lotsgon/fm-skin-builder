from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Iterable
import json

from .css_utils import load_css_selector_overrides, load_css_vars
from .logger import get_logger

log = get_logger(__name__)

__all__ = [
    "CssFileOverrides",
    "CollectedCss",
    "collect_css_from_dir",
    "load_targeting_hints",
]


@dataclass(frozen=True)
class CssFileOverrides:
    """Stores variables and selector overrides parsed from a single CSS/USS file."""

    vars: Dict[str, str]
    selectors: Dict[Tuple[str, str], str]
    source: Optional[Path] = None


@dataclass
class CollectedCss:
    """Aggregated CSS data including optional per-stylesheet scoping information."""

    global_vars: Dict[str, str] = field(default_factory=dict)
    global_selectors: Dict[Tuple[str, str], str] = field(
        default_factory=dict
    )
    asset_map: Dict[str, List[CssFileOverrides]] = field(default_factory=dict)
    files_by_stem: Dict[str, List[CssFileOverrides]
                        ] = field(default_factory=dict)

    @classmethod
    def from_overrides(
        cls,
        *,
        global_vars: Optional[Dict[str, str]] = None,
        global_selectors: Optional[Dict[Tuple[str, str], str]] = None,
        asset_map: Optional[Dict[str, Iterable[CssFileOverrides]]] = None,
        files_by_stem: Optional[Dict[str, Iterable[CssFileOverrides]]] = None,
    ) -> "CollectedCss":
        data = cls()
        if global_vars:
            data.global_vars.update(global_vars)
        if global_selectors:
            data.global_selectors.update(global_selectors)
        if asset_map:
            data.asset_map = {
                k.lower(): list(v)
                for k, v in asset_map.items()
            }
        if files_by_stem:
            data.files_by_stem = {
                k.lower(): list(v)
                for k, v in files_by_stem.items()
            }
        return data

    def clone_asset_map(self) -> Dict[str, List[CssFileOverrides]]:
        return {k: list(v) for k, v in self.asset_map.items()}

    def clone_files_by_stem(self) -> Dict[str, List[CssFileOverrides]]:
        return {k: list(v) for k, v in self.files_by_stem.items()}


def _load_css_mapping(css_dir: Path) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    candidates = [css_dir / "mapping.json"]
    colours = css_dir / "colours"
    if colours.exists():
        candidates.append(colours / "mapping.json")

    for path in candidates:
        if not path.exists():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Failed to read CSS mapping file %s: %s", path, exc)
            continue
        if not isinstance(loaded, dict):
            log.warning("CSS mapping file must contain an object: %s", path)
            continue
        for key, value in loaded.items():
            if not isinstance(key, str):
                continue
            file_key = key.strip().lower()
            targets: List[str] = []
            if isinstance(value, str):
                targets = [value]
            elif isinstance(value, list):
                targets = [str(item)
                           for item in value if isinstance(item, (str, int))]
            elif isinstance(value, dict):
                # Allow {"stylesheets": [...]} for future extensibility
                if "stylesheets" in value and isinstance(value["stylesheets"], list):
                    targets = [
                        str(item)
                        for item in value["stylesheets"]
                        if isinstance(item, (str, int))
                    ]
            if not targets:
                continue
            mapping.setdefault(file_key, [])
            mapping[file_key].extend(targets)
    return mapping


def _normalise_mapping_targets(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for val in values:
        norm = str(val).strip().lower()
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        result.append(norm)
    return result


def _mapping_targets_for_file(
    css_file: Path, css_dir: Path, mapping: Dict[str, List[str]]
) -> List[str]:
    if not mapping:
        return []
    variants = {
        css_file.name.lower(),
        css_file.stem.lower(),
    }
    try:
        rel = css_file.relative_to(css_dir)
        variants.add(str(rel).replace("\\", "/").lower())
    except ValueError:
        # It's expected that css_file may not be relative to css_dir; ignore and continue.
        pass
    matches: List[str] = []
    for variant in variants:
        if variant in mapping:
            matches.extend(mapping[variant])
        if not variant.endswith(".css") and not variant.endswith(".uss"):
            if variant in mapping:
                matches.extend(mapping[variant])
            if (variant + ".css") in mapping:
                matches.extend(mapping[variant + ".css"])
            if (variant + ".uss") in mapping:
                matches.extend(mapping[variant + ".uss"])
    return _normalise_mapping_targets(matches)


def collect_css_from_dir(css_dir: Path) -> CollectedCss:
    """Collect CSS variable data and optional stylesheet mappings from a directory."""

    collected = CollectedCss()
    mapping = _load_css_mapping(css_dir)

    files: List[Path] = []
    if (css_dir / "config.json").exists():
        colours = css_dir / "colours"
        if colours.exists():
            files.extend(sorted(colours.glob("*.uss")))
            files.extend(sorted(colours.glob("*.css")))
        files.extend(sorted(css_dir.glob("*.uss")))
        files.extend(sorted(css_dir.glob("*.css")))
    else:
        files.extend(sorted(css_dir.glob("*.uss")))
        files.extend(sorted(css_dir.glob("*.css")))

    total_vars = 0
    total_selectors = 0

    for css_file in files:
        try:
            file_vars = load_css_vars(css_file)
            file_selectors = load_css_selector_overrides(css_file)
        except Exception as exc:
            log.warning("Failed to parse %s: %s", css_file, exc)
            continue

        overrides = CssFileOverrides(
            vars=file_vars, selectors=file_selectors, source=css_file)

        total_vars += len(file_vars)
        total_selectors += len(file_selectors)

        targets = _mapping_targets_for_file(css_file, css_dir, mapping)
        if targets:
            for target in targets:
                collected.asset_map.setdefault(target, []).append(overrides)
        else:
            collected.global_vars.update(file_vars)
            collected.global_selectors.update(file_selectors)

        stem_key = css_file.stem.lower()
        collected.files_by_stem.setdefault(stem_key, []).append(overrides)

    log.info(
        "Total CSS vars: %s, selector overrides: %s from %s files",
        total_vars,
        total_selectors,
        len(files),
    )
    return collected


def load_targeting_hints(
    css_dir: Path,
) -> Tuple[
    Optional[Set[str]],
    Optional[Set[str]],
    Optional[Set[Tuple[str, str]]],
]:
    """Load optional targeting hints from a skin or CSS directory."""
    hints_path = css_dir / "hints.txt"
    if not hints_path.exists():
        return None, None, None

    assets: Set[str] = set()
    selectors: Set[str] = set()
    selector_props: Set[Tuple[str, str]] = set()

    try:
        for raw in hints_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            match_asset = re.match(
                r"^asset\s*[:=]\s*(.+)$", line, re.IGNORECASE)
            if match_asset:
                names = [item.strip() for item in re.split(
                    r",|;", match_asset.group(1)) if item.strip()]
                assets.update(names)
                continue
            match_selector = re.match(
                r"^selector\s*[:=]\s*(.+)$", line, re.IGNORECASE)
            if match_selector:
                rest = match_selector.group(1).strip()
                if " " in rest:
                    selector, prop = rest.split(None, 1)
                    selectors.add(selector.strip())
                    selector_props.add((selector.strip(), prop.strip()))
                else:
                    selectors.add(rest)
    except Exception as exc:
        log.warning("Failed to parse targeting hints at %s: %s",
                    hints_path, exc)

    return assets or None, selectors or None, selector_props or None
