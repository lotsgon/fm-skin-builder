"""
Catalogue Builder

Main orchestrator that coordinates all extraction, processing, and export phases.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .extractors import CSSExtractor, SpriteExtractor, TextureExtractor, FontExtractor
from .models import (
    CatalogueMetadata,
    CSSVariable,
    CSSClass,
    Sprite,
    Texture,
    Font,
)
from .content_hasher import compute_hash
from .color_extractor import extract_dominant_colors
from .image_processor import ImageProcessor
from .auto_tagger import generate_tags
from .search_builder import SearchIndexBuilder
from .deduplicator import deduplicate_by_filename
from .exporter import CatalogueExporter, create_version_directory_name
from ..logger import get_logger


log = get_logger(__name__)


class CatalogueBuilder:
    """Orchestrates the full catalogue building process."""

    def __init__(
        self,
        fm_version: str,
        output_dir: Path,
        icon_white_path: Path,
        icon_black_path: Path,
        catalogue_version: int = 1,
        pretty_json: bool = False,
    ):
        """
        Initialize catalogue builder.

        Args:
            fm_version: FM version string (e.g., "2026.4.0")
            output_dir: Base output directory
            icon_white_path: Path to white watermark icon
            icon_black_path: Path to black watermark icon
            catalogue_version: Catalogue version number
            pretty_json: Pretty-print JSON
        """
        self.fm_version = fm_version
        self.catalogue_version = catalogue_version
        self.base_output_dir = output_dir
        self.pretty_json = pretty_json

        # Create version-specific output directory
        version_dir_name = create_version_directory_name(fm_version, catalogue_version)
        self.output_dir = output_dir / version_dir_name

        # Initialize components
        self.css_extractor = CSSExtractor(fm_version)
        self.sprite_extractor = SpriteExtractor(fm_version)
        self.texture_extractor = TextureExtractor(fm_version)
        self.font_extractor = FontExtractor(fm_version)
        self.image_processor = ImageProcessor(icon_white_path, icon_black_path)
        self.search_builder = SearchIndexBuilder()
        self.exporter = CatalogueExporter(self.output_dir, pretty_json)

        # Storage for extracted assets
        self.bundles_scanned: List[str] = []
        self.css_variables: List[CSSVariable] = []
        self.css_classes: List[CSSClass] = []
        self.sprites: List[Sprite] = []
        self.textures: List[Texture] = []
        self.fonts: List[Font] = []

        # Early deduplication cache (hash -> processed asset data)
        self._sprite_hash_cache: Dict[str, Dict[str, Any]] = {}
        self._texture_hash_cache: Dict[str, Dict[str, Any]] = {}

    def build(self, bundle_paths: List[Path]) -> None:
        """
        Build complete catalogue from bundles.

        Args:
            bundle_paths: List of paths to .bundle files or directories containing bundles
        """
        log.info(f"Building catalogue for FM {self.fm_version} v{self.catalogue_version}")

        # Expand directories to bundle files
        bundles = self._expand_bundle_paths(bundle_paths)
        log.info(f"Found {len(bundles)} bundles to scan")

        # Phase 1: Extract raw data from bundles
        log.info("Phase 1: Extracting assets from bundles...")
        self._extract_from_bundles(bundles)

        # Phase 2: Process images (thumbnails, colors)
        log.info("Phase 2: Processing images...")
        self._process_images()

        # Phase 3: Deduplicate assets
        log.info("Phase 3: Deduplicating assets...")
        self._deduplicate_assets()

        # Phase 4: Build search indices
        log.info("Phase 4: Building search indices...")
        search_index = self.search_builder.build_index(
            self.css_variables, self.css_classes, self.sprites, self.textures
        )

        # Phase 5: Create metadata
        log.info("Phase 5: Creating metadata...")
        metadata = self._create_metadata()

        # Phase 6: Export to JSON
        log.info("Phase 6: Exporting to JSON...")
        self.exporter.export(
            metadata,
            self.css_variables,
            self.css_classes,
            self.sprites,
            self.textures,
            self.fonts,
            search_index,
        )

        log.info(f"✅ Catalogue built successfully: {self.output_dir}")
        log.info(f"   - {len(self.css_variables)} CSS variables")
        log.info(f"   - {len(self.css_classes)} CSS classes")
        log.info(f"   - {len(self.sprites)} sprites")
        log.info(f"   - {len(self.textures)} textures")
        log.info(f"   - {len(self.fonts)} fonts")

    def _expand_bundle_paths(self, paths: List[Path]) -> List[Path]:
        """Expand directories to .bundle files."""
        bundles = []
        for path in paths:
            if path.is_dir():
                bundles.extend(sorted(path.glob("**/*.bundle")))
            elif path.suffix == ".bundle":
                bundles.append(path)
        return bundles

    def _extract_from_bundles(self, bundles: List[Path]) -> None:
        """Extract assets from all bundles."""
        import gc

        for bundle_path in bundles:
            log.info(f"  Scanning: {bundle_path.name}")

            try:
                self.bundles_scanned.append(bundle_path.name)

                # Extract CSS
                try:
                    css_data = self.css_extractor.extract_from_bundle(bundle_path)
                    self.css_variables.extend(css_data.get("variables", []))
                    self.css_classes.extend(css_data.get("classes", []))
                except Exception as e:
                    log.warning(f"  Error extracting CSS from {bundle_path.name}: {e}")

                # Extract sprites (returns raw data, not models yet)
                try:
                    sprite_data_list = self.sprite_extractor.extract_from_bundle(bundle_path)
                    if not hasattr(self, '_sprite_data'):
                        self._sprite_data = []
                    self._sprite_data.extend(sprite_data_list)
                except Exception as e:
                    log.warning(f"  Error extracting sprites from {bundle_path.name}: {e}")

                # Extract textures (returns raw data)
                try:
                    texture_data_list = self.texture_extractor.extract_from_bundle(bundle_path)
                    if not hasattr(self, '_texture_data'):
                        self._texture_data = []
                    self._texture_data.extend(texture_data_list)
                except Exception as e:
                    log.warning(f"  Error extracting textures from {bundle_path.name}: {e}")

                # Extract fonts
                try:
                    self.fonts.extend(self.font_extractor.extract_from_bundle(bundle_path))
                except Exception as e:
                    log.warning(f"  Error extracting fonts from {bundle_path.name}: {e}")

            except Exception as e:
                log.error(f"  Critical error scanning {bundle_path.name}: {e}")
                import traceback
                log.debug(traceback.format_exc())

            # Force garbage collection after each bundle to prevent memory issues
            finally:
                gc.collect()

    def _process_images(self) -> None:
        """Process images to create thumbnails and extract colors."""
        sprites_processed = 0
        sprites_skipped = 0
        textures_processed = 0
        textures_skipped = 0

        # Process sprites
        if hasattr(self, '_sprite_data'):
            for sprite_data in self._sprite_data:
                try:
                    sprite, was_cached = self._process_sprite_image(sprite_data)
                    if sprite:
                        self.sprites.append(sprite)
                        if was_cached:
                            sprites_skipped += 1
                        else:
                            sprites_processed += 1
                except Exception as e:
                    log.warning(f"  Error processing sprite {sprite_data.get('name')}: {e}")

        # Process textures
        if hasattr(self, '_texture_data'):
            for texture_data in self._texture_data:
                try:
                    texture, was_cached = self._process_texture_image(texture_data)
                    if texture:
                        self.textures.append(texture)
                        if was_cached:
                            textures_skipped += 1
                        else:
                            textures_processed += 1
                except Exception as e:
                    log.warning(f"  Error processing texture {texture_data.get('name')}: {e}")

        log.info(f"  Sprites: {sprites_processed} processed, {sprites_skipped} deduplicated (skipped)")
        log.info(f"  Textures: {textures_processed} processed, {textures_skipped} deduplicated (skipped)")

    def _process_sprite_image(self, sprite_data: Dict[str, Any]) -> tuple[Optional[Sprite], bool]:
        """
        Process sprite image data to create Sprite model.

        Returns:
            Tuple of (Sprite, was_cached) where was_cached indicates if processing was skipped
        """
        image_data = sprite_data.get('image_data')
        if not image_data:
            # No image data (e.g., atlas sprite)
            # Create sprite without thumbnail
            sprite = Sprite(
                name=sprite_data['name'],
                aliases=[],
                has_vertex_data=sprite_data.get('has_vertex_data', False),
                content_hash="",
                thumbnail_path="",
                width=sprite_data.get('width', 0),
                height=sprite_data.get('height', 0),
                dominant_colors=[],
                tags=generate_tags(sprite_data['name']),
                atlas=sprite_data.get('atlas'),
                bundles=[sprite_data['bundle']],
                first_seen=self.fm_version,
                last_seen=self.fm_version,
            )
            return sprite, False

        # Compute hash FIRST (cheap operation)
        content_hash = compute_hash(image_data)

        # Check if we've already processed this hash
        if content_hash in self._sprite_hash_cache:
            # Reuse cached data
            cached = self._sprite_hash_cache[content_hash]
            sprite = Sprite(
                name=sprite_data['name'],
                aliases=[],
                has_vertex_data=sprite_data.get('has_vertex_data', False),
                content_hash=content_hash,
                thumbnail_path=cached['thumbnail_path'],
                width=cached['width'],
                height=cached['height'],
                dominant_colors=cached['dominant_colors'],
                tags=generate_tags(sprite_data['name']),
                atlas=sprite_data.get('atlas'),
                bundles=[sprite_data['bundle']],
                first_seen=self.fm_version,
                last_seen=self.fm_version,
            )
            return sprite, True

        # Not cached - process image (expensive operation)
        thumbnail_filename = f"{content_hash}.webp"
        thumbnail_path = self.output_dir / "thumbnails" / "sprites" / thumbnail_filename
        original_size = self.image_processor.create_thumbnail(image_data, thumbnail_path)

        # Extract dominant colors
        dominant_colors = extract_dominant_colors(image_data, num_colors=5)

        # Cache the processed data
        self._sprite_hash_cache[content_hash] = {
            'thumbnail_path': f"thumbnails/sprites/{thumbnail_filename}",
            'width': sprite_data.get('width', original_size[0]),
            'height': sprite_data.get('height', original_size[1]),
            'dominant_colors': dominant_colors,
        }

        # Generate tags
        tags = generate_tags(sprite_data['name'])

        sprite = Sprite(
            name=sprite_data['name'],
            aliases=[],
            has_vertex_data=sprite_data.get('has_vertex_data', False),
            content_hash=content_hash,
            thumbnail_path=f"thumbnails/sprites/{thumbnail_filename}",
            width=sprite_data.get('width', original_size[0]),
            height=sprite_data.get('height', original_size[1]),
            dominant_colors=dominant_colors,
            tags=tags,
            atlas=sprite_data.get('atlas'),
            bundles=[sprite_data['bundle']],
            first_seen=self.fm_version,
            last_seen=self.fm_version,
        )
        return sprite, False

    def _process_texture_image(self, texture_data: Dict[str, Any]) -> tuple[Optional[Texture], bool]:
        """
        Process texture image data to create Texture model.

        Returns:
            Tuple of (Texture, was_cached) where was_cached indicates if processing was skipped
        """
        image_data = texture_data.get('image_data')
        if not image_data:
            return None, False

        # Compute hash FIRST (cheap operation)
        content_hash = compute_hash(image_data)

        # Check if we've already processed this hash
        if content_hash in self._texture_hash_cache:
            # Reuse cached data
            cached = self._texture_hash_cache[content_hash]
            texture = Texture(
                name=texture_data['name'],
                aliases=[],
                content_hash=content_hash,
                thumbnail_path=cached['thumbnail_path'],
                type=texture_data.get('type', 'texture'),
                width=cached['width'],
                height=cached['height'],
                dominant_colors=cached['dominant_colors'],
                tags=generate_tags(texture_data['name']),
                bundles=[texture_data['bundle']],
                first_seen=self.fm_version,
                last_seen=self.fm_version,
            )
            return texture, True

        # Not cached - process image (expensive operation)
        thumbnail_filename = f"{content_hash}.webp"
        thumbnail_path = self.output_dir / "thumbnails" / "textures" / thumbnail_filename
        original_size = self.image_processor.create_thumbnail(image_data, thumbnail_path)

        # Extract dominant colors
        dominant_colors = extract_dominant_colors(image_data, num_colors=5)

        # Cache the processed data
        self._texture_hash_cache[content_hash] = {
            'thumbnail_path': f"thumbnails/textures/{thumbnail_filename}",
            'width': texture_data.get('width', original_size[0]),
            'height': texture_data.get('height', original_size[1]),
            'dominant_colors': dominant_colors,
        }

        # Generate tags
        tags = generate_tags(texture_data['name'])

        texture = Texture(
            name=texture_data['name'],
            aliases=[],
            content_hash=content_hash,
            thumbnail_path=f"thumbnails/textures/{thumbnail_filename}",
            type=texture_data.get('type', 'texture'),
            width=texture_data.get('width', original_size[0]),
            height=texture_data.get('height', original_size[1]),
            dominant_colors=dominant_colors,
            tags=tags,
            bundles=[texture_data['bundle']],
            first_seen=self.fm_version,
            last_seen=self.fm_version,
        )
        return texture, False

    def _deduplicate_assets(self) -> None:
        """Deduplicate assets by filename patterns."""
        # Deduplicate sprites
        sprite_names = [s.name for s in self.sprites]
        sprite_dedup = deduplicate_by_filename(sprite_names)

        # Update sprites with aliases
        sprite_map = {s.name: s for s in self.sprites}
        deduplicated_sprites = []

        for primary, aliases in sprite_dedup.items():
            if primary in sprite_map:
                sprite = sprite_map[primary]
                sprite.aliases = aliases
                deduplicated_sprites.append(sprite)

        self.sprites = deduplicated_sprites
        log.info(f"  Deduplicated {len(sprite_names)} sprites to {len(self.sprites)}")

        # Deduplicate textures
        texture_names = [t.name for t in self.textures]
        texture_dedup = deduplicate_by_filename(texture_names)

        texture_map = {t.name: t for t in self.textures}
        deduplicated_textures = []

        for primary, aliases in texture_dedup.items():
            if primary in texture_map:
                texture = texture_map[primary]
                texture.aliases = aliases
                deduplicated_textures.append(texture)

        self.textures = deduplicated_textures
        log.info(f"  Deduplicated {len(texture_names)} textures to {len(self.textures)}")

    def _create_metadata(self) -> CatalogueMetadata:
        """Create catalogue metadata."""
        return CatalogueMetadata(
            catalogue_version=self.catalogue_version,
            fm_version=self.fm_version,
            schema_version="1.0.0",
            generated_at=datetime.utcnow(),
            bundles_scanned=self.bundles_scanned,
            total_assets={
                "css_variables": len(self.css_variables),
                "css_classes": len(self.css_classes),
                "sprites": len(self.sprites),
                "textures": len(self.textures),
                "fonts": len(self.fonts),
            },
        )
