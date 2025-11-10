"""
Auto Tagger

Generates tags from asset names using pattern matching.
"""

from __future__ import annotations
import re
from typing import List


# Pattern matching rules for tag generation
TAG_PATTERNS = {
    'icon_': ['icon'],
    'ico_': ['icon'],
    'bg_': ['background'],
    'background_': ['background'],
    'btn_': ['button', 'ui'],
    'button_': ['button', 'ui'],
    '_player': ['player', 'person'],
    '_team': ['team', 'club'],
    '_staff': ['staff', 'person'],
    '_club': ['club', 'team'],
    '_star': ['star', 'rating'],
    '_rating': ['rating'],
    'grass': ['grass', 'pitch', 'field'],
    'pitch': ['pitch', 'field'],
    'primary': ['primary', 'main'],
    'secondary': ['secondary', 'alternate'],
    'header': ['header', 'ui'],
    'footer': ['footer', 'ui'],
    'menu': ['menu', 'ui'],
    'panel': ['panel', 'ui'],
    'card': ['card', 'ui'],
    'badge': ['badge', 'icon'],
    'avatar': ['avatar', 'person'],
}


def generate_tags(name: str) -> List[str]:
    """
    Generate tags from asset name.

    Args:
        name: Asset name (e.g., "icon_player_primary")

    Returns:
        List of tags (e.g., ["icon", "player", "person", "primary", "main"])
    """
    tags = set()
    name_lower = name.lower()

    # Apply pattern matching
    for pattern, pattern_tags in TAG_PATTERNS.items():
        if pattern in name_lower:
            tags.update(pattern_tags)

    # Split on common delimiters and add parts as tags
    # Support: underscores, hyphens, and camelCase
    parts = re.split(r'[_\-]|(?<=[a-z])(?=[A-Z])', name)

    for part in parts:
        if len(part) > 2:  # Skip very short parts
            clean_part = part.lower().strip()
            if clean_part and not clean_part.isdigit():
                tags.add(clean_part)

    # Remove generic/useless tags
    remove_tags = {'the', 'and', 'or', 'for', 'to', 'of', 'in', 'on', 'at', 'by'}
    tags = tags - remove_tags

    return sorted(list(tags))


def generate_css_tags(selector: str) -> List[str]:
    """
    Generate tags from CSS selector.

    Args:
        selector: CSS selector (e.g., ".button-primary")

    Returns:
        List of tags
    """
    # Remove leading . or #
    clean = selector.lstrip('.#')

    # Split by - or _
    parts = re.split(r'[-_]', clean)

    tags = []
    for part in parts:
        if len(part) > 2:
            tags.append(part.lower())

    return tags
