"""
Core data models for the asset catalogue system.

These Pydantic models define the structure of all extracted assets
and metadata for export to R2-compatible JSON files.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AssetStatus(str, Enum):
    """Asset lifecycle status."""

    ACTIVE = "active"  # Currently in game
    REMOVED = "removed"  # Was in game, now removed (kept in catalogue)
    MODIFIED = "modified"  # Changed between versions


class CatalogueMetadata(BaseModel):
    """Metadata about the entire catalogue."""

    fm_version: str = Field(..., description="FM game version (e.g., '2026.4.0')")
    schema_version: str = Field(
        default="2.1.0", description="Catalogue data format version"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    bundles_scanned: List[str] = Field(default_factory=list)
    total_assets: Dict[str, int] = Field(
        default_factory=dict,
        description="Asset counts by type: {'sprites': 2450, 'textures': 820, ...}",
    )
    previous_fm_version: Optional[str] = Field(
        None, description="Previous FM version for changelog generation"
    )
    changes_since_previous: Optional[Dict[str, Any]] = Field(
        None, description="Detailed change summary from previous version"
    )


class CSSValueDefinition(BaseModel):
    """Individual CSS value (Unity USS supports multi-value properties)."""

    value_type: int = Field(
        ..., description="Unity type: 3=dimension, 4=color, 8=string, 10=variable"
    )
    index: int = Field(..., description="Index in strings/colors array")
    resolved_value: str = Field(
        ..., description="Human-readable: '#1976d2' or 'var(--primary)' or '10px'"
    )
    raw_value: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw Unity data: {r: 0.098, g: 0.463, b: 0.824, a: 1.0} for colors",
    )

    def __str__(self) -> str:
        return self.resolved_value


class CSSProperty(BaseModel):
    """CSS property with one or more values."""

    name: str = Field(..., description="Property name: 'background-color'")
    values: List[CSSValueDefinition] = Field(default_factory=list)

    @property
    def css_notation(self) -> str:
        """Render as CSS string."""
        value_str = ", ".join(str(v) for v in self.values)
        return f"{self.name}: {value_str};"


class CSSVariable(BaseModel):
    """CSS custom property (CSS variable)."""

    name: str = Field(..., description="Variable name: '--primary-color'")
    stylesheet: str = Field(..., description="Unity asset name: 'FMColours'")
    bundle: str = Field(..., description="Bundle filename: 'skins.bundle'")
    property_name: str = Field(..., description="Property: 'background-color'")
    rule_index: int = Field(..., description="Rule index in stylesheet")

    # Multi-value support
    values: List[CSSValueDefinition] = Field(default_factory=list)

    # Reverse engineering indices
    string_index: Optional[int] = Field(
        None, description="Index in strings array (type 3/8/10)"
    )
    color_index: Optional[int] = Field(
        None, description="Index in colors array (type 4)"
    )

    # Extracted colors for search
    colors: List[str] = Field(
        default_factory=list, description="Hex colors only: ['#1976d2']"
    )

    # Version tracking
    status: AssetStatus = AssetStatus.ACTIVE
    first_seen: str = Field(..., description="FM version first appeared: '2026.1.0'")
    last_seen: str = Field(..., description="FM version last seen: '2026.4.0'")
    modified_in: Optional[str] = Field(
        None, description="FM version modified: '2026.3.0'"
    )

    # Change tracking (schema 2.1.0+) - vs previous stable version
    change_status: Optional[str] = Field(
        None, description="Change status: 'new', 'modified', 'unchanged'"
    )
    changed_in_version: Optional[str] = Field(
        None, description="Version where this change occurred"
    )
    previous_values: Optional[str] = Field(
        None, description="Previous values for modified assets"
    )


class CSSClass(BaseModel):
    """CSS class selector with properties."""

    name: str = Field(..., description="Selector: '.button-primary'")
    stylesheet: str = Field(..., description="Unity asset name: 'FMColours'")
    bundle: str
    properties: List[CSSProperty] = Field(default_factory=list)
    variables_used: List[str] = Field(
        default_factory=list,
        description="CSS variables referenced: ['--primary-color', '--button-bg']",
    )
    tags: List[str] = Field(
        default_factory=list, description="Auto-tags: ['button', 'primary', 'ui']"
    )

    status: AssetStatus = AssetStatus.ACTIVE
    first_seen: str
    last_seen: str

    # Change tracking (schema 2.1.0+) - vs previous stable version
    change_status: Optional[str] = Field(
        None, description="Change status: 'new', 'modified', 'unchanged'"
    )
    changed_in_version: Optional[str] = Field(
        None, description="Version where this change occurred"
    )


class Sprite(BaseModel):
    """Sprite/icon asset."""

    name: str = Field(..., description="Primary name")
    aliases: List[str] = Field(
        default_factory=list,
        description="Size variants: ['icon_player_16', 'icon_player_24']",
    )
    has_vertex_data: bool = Field(
        default=False, description="True = vector sprite (custom mesh data)"
    )
    content_hash: str = Field(..., description="SHA256 for integrity")
    thumbnail_path: str = Field(
        ..., description="Relative path: 'thumbnails/sprites/{hash}.webp'"
    )
    width: int
    height: int

    # Color palette (3-5 dominant colors)
    dominant_colors: List[str] = Field(
        default_factory=list,
        description="Hex colors: ['#1976d2', '#ffffff', '#000000']",
    )

    # Auto-tags
    tags: List[str] = Field(
        default_factory=list, description="['icon', 'player', 'sport']"
    )

    atlas: Optional[str] = Field(
        None, description="SpriteAtlas reference if applicable"
    )
    bundles: List[str] = Field(default_factory=list)

    status: AssetStatus = AssetStatus.ACTIVE
    first_seen: str
    last_seen: str

    # Change tracking (schema 2.1.0+) - vs previous stable version
    change_status: Optional[str] = Field(
        None, description="Change status: 'new', 'modified', 'unchanged'"
    )
    changed_in_version: Optional[str] = Field(
        None, description="Version where this change occurred"
    )
    previous_content_hash: Optional[str] = Field(
        None, description="Previous content hash for modified sprites"
    )


class Texture(BaseModel):
    """Texture asset (backgrounds, UI textures)."""

    name: str
    aliases: List[str] = Field(default_factory=list)
    content_hash: str
    thumbnail_path: str = Field(
        ..., description="Relative path: 'thumbnails/textures/{hash}.webp'"
    )
    type: str = Field(default="texture", description="'background', 'icon', 'texture'")
    width: int
    height: int
    dominant_colors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    bundles: List[str] = Field(default_factory=list)

    status: AssetStatus = AssetStatus.ACTIVE
    first_seen: str
    last_seen: str

    # Change tracking (schema 2.1.0+) - vs previous stable version
    change_status: Optional[str] = Field(
        None, description="Change status: 'new', 'modified', 'unchanged'"
    )
    changed_in_version: Optional[str] = Field(
        None, description="Version where this change occurred"
    )
    previous_content_hash: Optional[str] = Field(
        None, description="Previous content hash for modified textures"
    )


class Font(BaseModel):
    """Font asset."""

    name: str
    bundles: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    status: AssetStatus = AssetStatus.ACTIVE
    first_seen: str
    last_seen: str

    # Change tracking (schema 2.1.0+) - vs previous stable version
    change_status: Optional[str] = Field(
        None, description="Change status: 'new', 'modified', 'unchanged'"
    )
    changed_in_version: Optional[str] = Field(
        None, description="Version where this change occurred"
    )
