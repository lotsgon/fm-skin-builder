"""
Deduplicator

Filename-based deduplication using wildcard pattern matching.
Handles size variants like icon_player_16, icon_player_24 -> icon_player
"""

from __future__ import annotations
import re
from typing import Dict, List


def deduplicate_by_filename(names: List[str]) -> Dict[str, List[str]]:
    """
    Deduplicate filenames by removing size suffixes.

    Args:
        names: List of asset names

    Returns:
        Dictionary mapping primary names to aliases
        e.g., {"icon_player": ["icon_player_16", "icon_player_24"]}
    """
    groups: Dict[str, List[str]] = {}

    for name in names:
        base = _get_base_name(name)

        if base not in groups:
            groups[base] = []
        groups[base].append(name)

    # Build result: primary name -> aliases
    result = {}
    for base, variants in groups.items():
        if len(variants) == 1:
            # No duplicates - just use the name as-is
            result[variants[0]] = []
        else:
            # Multiple variants - pick primary and list others as aliases
            # Primary = shortest variant (likely the base without size suffix)
            # Or if base exists in variants, use that
            if base in variants:
                primary = base
            else:
                primary = min(variants, key=len)

            aliases = [v for v in variants if v != primary]
            result[primary] = aliases

    return result


def _get_base_name(name: str) -> str:
    """
    Extract base name by removing size suffixes.

    Examples:
        icon_player_16 -> icon_player
        icon_player_24 -> icon_player
        bg_grass@2x -> bg_grass
        texture_512 -> texture

    Args:
        name: Asset name

    Returns:
        Base name without size suffixes
    """
    # Remove common size suffixes
    # Pattern: _\d+x?\d* (e.g., _16, _24, _32, _64, _128x128)
    # Pattern: @\dx (e.g., @2x, @3x)
    base = re.sub(r'_\d+x?\d*(@\dx)?$', '', name)
    base = re.sub(r'@\dx$', '', base)

    return base
