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
from .exporter import CatalogueExporter
from .version_differ import VersionDiffer
from ..logger import get_logger

log = get_logger(__name__)

try:
    from packaging.version import Version, InvalidVersion
except ImportError:
    # Fallback if packaging not available
    log.warning("packaging library not found - version comparison may be inaccurate")
    Version = None
    InvalidVersion = Exception


class CatalogueBuilder:
    """Orchestrates the full catalogue building process."""

    def __init__(
        self,
        fm_version: str,
        output_dir: Path,
        icon_white_path: Path,
        icon_black_path: Path,
        pretty_json: bool = False,
        previous_version: Optional[str] = None,
        skip_changelog: bool = False,
        r2_config: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize catalogue builder.

        Args:
            fm_version: FM version string (e.g., "2026.4.0")
            output_dir: Base output directory (catalogue will be created in fm_version subdirectory)
            icon_white_path: Path to white watermark icon
            icon_black_path: Path to black watermark icon
            pretty_json: Pretty-print JSON
            previous_version: Override previous version for comparison (default: auto-detect)
            skip_changelog: Skip changelog generation
            r2_config: R2 configuration dict with keys: endpoint, bucket, access_key, secret_key, base_path
        """
        self.fm_version = fm_version
        self.base_output_dir = output_dir
        self.pretty_json = pretty_json
        self.previous_version_override = previous_version
        self.skip_changelog = skip_changelog
        self.r2_config = r2_config or {}

        # Create version-specific output directory (just FM version, no -vN suffix)
        self.output_dir = output_dir / fm_version

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

        # Changelog metadata (populated during changelog generation)
        self._changelog_metadata: Optional[Dict[str, Any]] = None

    def build(self, bundle_paths: List[Path]) -> None:
        """
        Build complete catalogue from bundles.

        Args:
            bundle_paths: List of paths to .bundle files or directories containing bundles
        """
        log.info(f"Building catalogue for FM {self.fm_version}")

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

        # Phase 4: Generate changelog and apply change tracking
        log.info("Phase 4: Generating changelog and applying change tracking...")
        changelog = self._generate_changelog_if_needed()
        if changelog:
            self._apply_change_tracking(changelog)

        # Phase 5: Build search indices (including change filters)
        log.info("Phase 5: Building search indices...")
        search_index = self.search_builder.build_index(
            self.css_variables,
            self.css_classes,
            self.sprites,
            self.textures,
            self.fonts,
        )

        # Phase 6: Create metadata
        log.info("Phase 6: Creating metadata...")
        metadata = self._create_metadata()

        # Phase 7: Export to JSON (with change_status in assets)
        log.info("Phase 7: Exporting to JSON...")
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
        """
        Expand directories to .bundle files, excluding backup/modified files.

        Excludes:
        - Files ending with _modified.bundle
        - Files ending with .bak
        - Files ending with .bundle.bak
        """
        bundles = []
        excluded_patterns = [
            "_modified.bundle",
            ".bak",
            ".bundle.bak",
            "_temp.bundle",
            ".tmp",
        ]

        for path in paths:
            if path.is_dir():
                for bundle in sorted(path.glob("**/*.bundle")):
                    # Check if bundle should be excluded
                    if any(
                        str(bundle).endswith(pattern) for pattern in excluded_patterns
                    ):
                        log.debug(f"  Skipping excluded bundle: {bundle.name}")
                        continue
                    bundles.append(bundle)
            elif path.suffix == ".bundle":
                # Check if this specific bundle should be excluded
                if any(str(path).endswith(pattern) for pattern in excluded_patterns):
                    log.warning(f"  Skipping excluded bundle: {path.name}")
                    continue
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
                    sprite_data_list = self.sprite_extractor.extract_from_bundle(
                        bundle_path
                    )
                    if not hasattr(self, "_sprite_data"):
                        self._sprite_data = []
                    self._sprite_data.extend(sprite_data_list)
                except Exception as e:
                    log.warning(
                        f"  Error extracting sprites from {bundle_path.name}: {e}"
                    )

                # Extract textures (returns raw data)
                try:
                    texture_data_list = self.texture_extractor.extract_from_bundle(
                        bundle_path
                    )
                    if not hasattr(self, "_texture_data"):
                        self._texture_data = []
                    self._texture_data.extend(texture_data_list)
                except Exception as e:
                    log.warning(
                        f"  Error extracting textures from {bundle_path.name}: {e}"
                    )

                # Extract fonts
                try:
                    self.fonts.extend(
                        self.font_extractor.extract_from_bundle(bundle_path)
                    )
                except Exception as e:
                    log.warning(
                        f"  Error extracting fonts from {bundle_path.name}: {e}"
                    )

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
        if hasattr(self, "_sprite_data"):
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
                    log.warning(
                        f"  Error processing sprite {sprite_data.get('name')}: {e}"
                    )

        # Process textures
        if hasattr(self, "_texture_data"):
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
                    log.warning(
                        f"  Error processing texture {texture_data.get('name')}: {e}"
                    )

        log.info(
            f"  Sprites: {sprites_processed} processed, {sprites_skipped} deduplicated (skipped)"
        )
        log.info(
            f"  Textures: {textures_processed} processed, {textures_skipped} deduplicated (skipped)"
        )

    def _process_sprite_image(
        self, sprite_data: Dict[str, Any]
    ) -> tuple[Optional[Sprite], bool]:
        """
        Process sprite image data to create Sprite model.

        Returns:
            Tuple of (Sprite, was_cached) where was_cached indicates if processing was skipped
        """
        image_data = sprite_data.get("image_data")
        if not image_data:
            # No image data (e.g., atlas sprite)
            # Create sprite without thumbnail
            sprite = Sprite(
                name=sprite_data["name"],
                aliases=[],
                has_vertex_data=sprite_data.get("has_vertex_data", False),
                content_hash="",
                thumbnail_path="",
                width=sprite_data.get("width", 0),
                height=sprite_data.get("height", 0),
                dominant_colors=[],
                tags=generate_tags(sprite_data["name"]),
                atlas=sprite_data.get("atlas"),
                bundles=[sprite_data["bundle"]],
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
                name=sprite_data["name"],
                aliases=[],
                has_vertex_data=sprite_data.get("has_vertex_data", False),
                content_hash=content_hash,
                thumbnail_path=cached["thumbnail_path"],
                width=cached["width"],
                height=cached["height"],
                dominant_colors=cached["dominant_colors"],
                tags=generate_tags(sprite_data["name"]),
                atlas=sprite_data.get("atlas"),
                bundles=[sprite_data["bundle"]],
                first_seen=self.fm_version,
                last_seen=self.fm_version,
            )
            return sprite, True

        # Not cached - process image (expensive operation)
        thumbnail_filename = f"{content_hash}.webp"
        thumbnail_path = self.output_dir / "thumbnails" / "sprites" / thumbnail_filename
        original_size = self.image_processor.create_thumbnail(
            image_data, thumbnail_path
        )

        # Extract dominant colors
        dominant_colors = extract_dominant_colors(image_data, num_colors=5)

        # Cache the processed data
        self._sprite_hash_cache[content_hash] = {
            "thumbnail_path": f"thumbnails/sprites/{thumbnail_filename}",
            "width": sprite_data.get("width", original_size[0]),
            "height": sprite_data.get("height", original_size[1]),
            "dominant_colors": dominant_colors,
        }

        # Generate tags
        tags = generate_tags(sprite_data["name"])

        sprite = Sprite(
            name=sprite_data["name"],
            aliases=[],
            has_vertex_data=sprite_data.get("has_vertex_data", False),
            content_hash=content_hash,
            thumbnail_path=f"thumbnails/sprites/{thumbnail_filename}",
            width=sprite_data.get("width", original_size[0]),
            height=sprite_data.get("height", original_size[1]),
            dominant_colors=dominant_colors,
            tags=tags,
            atlas=sprite_data.get("atlas"),
            bundles=[sprite_data["bundle"]],
            first_seen=self.fm_version,
            last_seen=self.fm_version,
        )
        return sprite, False

    def _process_texture_image(
        self, texture_data: Dict[str, Any]
    ) -> tuple[Optional[Texture], bool]:
        """
        Process texture image data to create Texture model.

        Returns:
            Tuple of (Texture, was_cached) where was_cached indicates if processing was skipped
        """
        image_data = texture_data.get("image_data")
        if not image_data:
            return None, False

        # Compute hash FIRST (cheap operation)
        content_hash = compute_hash(image_data)

        # Check if we've already processed this hash
        if content_hash in self._texture_hash_cache:
            # Reuse cached data
            cached = self._texture_hash_cache[content_hash]
            texture = Texture(
                name=texture_data["name"],
                aliases=[],
                content_hash=content_hash,
                thumbnail_path=cached["thumbnail_path"],
                type=texture_data.get("type", "texture"),
                width=cached["width"],
                height=cached["height"],
                dominant_colors=cached["dominant_colors"],
                tags=generate_tags(texture_data["name"]),
                bundles=[texture_data["bundle"]],
                first_seen=self.fm_version,
                last_seen=self.fm_version,
            )
            return texture, True

        # Not cached - process image (expensive operation)
        thumbnail_filename = f"{content_hash}.webp"
        thumbnail_path = (
            self.output_dir / "thumbnails" / "textures" / thumbnail_filename
        )
        original_size = self.image_processor.create_thumbnail(
            image_data, thumbnail_path
        )

        # Extract dominant colors
        dominant_colors = extract_dominant_colors(image_data, num_colors=5)

        # Cache the processed data
        self._texture_hash_cache[content_hash] = {
            "thumbnail_path": f"thumbnails/textures/{thumbnail_filename}",
            "width": texture_data.get("width", original_size[0]),
            "height": texture_data.get("height", original_size[1]),
            "dominant_colors": dominant_colors,
        }

        # Generate tags
        tags = generate_tags(texture_data["name"])

        texture = Texture(
            name=texture_data["name"],
            aliases=[],
            content_hash=content_hash,
            thumbnail_path=f"thumbnails/textures/{thumbnail_filename}",
            type=texture_data.get("type", "texture"),
            width=texture_data.get("width", original_size[0]),
            height=texture_data.get("height", original_size[1]),
            dominant_colors=dominant_colors,
            tags=tags,
            bundles=[texture_data["bundle"]],
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
        log.info(
            f"  Deduplicated {len(texture_names)} textures to {len(self.textures)}"
        )

    def _create_metadata(self) -> CatalogueMetadata:
        """Create catalogue metadata."""
        metadata = CatalogueMetadata(
            fm_version=self.fm_version,
            schema_version="2.1.0",
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

        # Add changelog metadata if available
        if self._changelog_metadata:
            metadata.previous_fm_version = self._changelog_metadata.get(
                "previous_fm_version"
            )
            metadata.changes_since_previous = self._changelog_metadata.get(
                "changes_since_previous"
            )

        return metadata

    def _parse_version_with_beta(self, version_str: str) -> tuple[Optional[Any], bool]:
        """
        Parse version string and detect if it's beta.

        Args:
            version_str: Version string like "2026.0.5" or "2026.0.5-beta" or "2026.0.4-v1"

        Returns:
            Tuple of (Version object or None, is_beta flag)

        Examples:
            "2026.0.5-beta" → (Version("2026.0.5b0"), True)
            "2026.0.5" → (Version("2026.0.5"), False)
            "2026.0.4-v1" → (Version("2026.0.4"), False)  # Old format
        """
        if Version is None:
            # Fallback: return None and False
            return None, False

        # Strip old -v1, -v2 suffixes from old format
        clean_version = version_str
        if "-v" in version_str:
            parts = version_str.split("-v")
            if len(parts) == 2 and parts[1].isdigit():
                # Old format like 2026.0.4-v1
                clean_version = parts[0]

        # Detect beta
        is_beta = "-beta" in clean_version

        # Convert to packaging.version format (2026.0.5-beta → 2026.0.5b0)
        if is_beta:
            clean_version = clean_version.replace("-beta", "b0")

        try:
            return Version(clean_version), is_beta
        except (InvalidVersion, Exception):
            log.warning(f"Invalid version format: {version_str}")
            return None, False

    def _find_previous_stable(self) -> Optional[Path]:
        """
        Find the most recent stable version before current version.

        Returns:
            Path to previous stable version directory, or None if not found
        """
        if not self.base_output_dir.exists():
            return None

        current_version, is_current_beta = self._parse_version_with_beta(
            self.fm_version
        )
        if not current_version:
            # Fallback to simple string comparison
            return self._find_previous_version_fallback()

        candidates = []

        for d in self.base_output_dir.iterdir():
            if not d.is_dir() or d.name == self.fm_version:
                continue

            parsed, is_beta = self._parse_version_with_beta(d.name)
            if not parsed or is_beta:
                # Skip betas when looking for stable versions
                continue

            if parsed < current_version:
                candidates.append((parsed, d))

        if not candidates:
            return None

        # Sort by version (highest first)
        candidates.sort(reverse=True, key=lambda x: x[0])
        prev_dir = candidates[0][1]

        log.info(f"  Found previous stable version: {prev_dir.name}")
        return prev_dir

    def _find_matching_beta(self) -> Optional[Path]:
        """
        Find beta version matching current stable version.

        Example: If building 2026.0.5, look for 2026.0.5-beta

        Returns:
            Path to matching beta directory, or None if not found
        """
        current_version, is_current_beta = self._parse_version_with_beta(
            self.fm_version
        )

        if is_current_beta or not current_version:
            # Current is beta or unparseable
            return None

        # Look for matching beta
        beta_name = f"{current_version.public}-beta"
        beta_path = self.base_output_dir / beta_name

        if beta_path.exists() and beta_path.is_dir():
            log.info(f"  Found matching beta version: {beta_name}")
            return beta_path

        return None

    def _find_previous_version_fallback(self) -> Optional[Path]:
        """
        Fallback method for finding previous version without semantic versioning.
        Uses simple string sorting.

        Returns:
            Path to previous version directory, or None if not found
        """
        if not self.base_output_dir.exists():
            return None

        version_dirs = [
            d
            for d in self.base_output_dir.iterdir()
            if d.is_dir() and d.name != self.fm_version
        ]

        if not version_dirs:
            return None

        # Sort by directory name
        version_dirs.sort(reverse=True)

        prev_dir = version_dirs[0]
        log.info(f"  Found previous version (fallback): {prev_dir.name}")
        return prev_dir

    def _try_download_previous_from_r2(self) -> None:
        """
        Try to download previous versions from R2 if not available locally.

        This downloads the comparison target(s) that will be needed for changelog generation.
        """
        from .r2_downloader import R2Downloader

        try:
            downloader = R2Downloader(
                endpoint_url=self.r2_config["endpoint"],
                bucket=self.r2_config["bucket"],
                access_key=self.r2_config.get("access_key"),
                secret_key=self.r2_config.get("secret_key"),
            )

            base_path = self.r2_config.get("base_path", "")

            # Determine which versions we might need
            current_version, is_current_beta = self._parse_version_with_beta(
                self.fm_version
            )

            # List local versions
            local_versions = [
                d.name
                for d in self.base_output_dir.iterdir()
                if d.is_dir() and d.name != self.fm_version
            ]

            # Check if we need to download previous stable
            if self.previous_version_override:
                # User specified explicit version
                versions_to_check = [self.previous_version_override]
            else:
                # Auto-detect what we'll need
                versions_to_check = []

                prev_stable = self._find_previous_stable()
                if prev_stable and prev_stable.name not in local_versions:
                    versions_to_check.append(prev_stable.name)

                if not is_current_beta:
                    # Building stable - might need beta version too
                    matching_beta = self._find_matching_beta()
                    if matching_beta and matching_beta.name not in local_versions:
                        versions_to_check.append(matching_beta.name)

            # Download needed versions
            for version in versions_to_check:
                version_dir = self.base_output_dir / version
                if (
                    not version_dir.exists()
                    or not (version_dir / "metadata.json").exists()
                ):
                    log.info(f"  Attempting to download version {version} from R2...")
                    if downloader.download_version(
                        version, self.base_output_dir, base_path
                    ):
                        log.info(f"  ✅ Successfully downloaded {version} from R2")
                    else:
                        log.warning(f"  ⚠️  Could not download {version} from R2")

        except Exception as e:
            log.warning(f"  ⚠️  R2 download failed: {e}")
            log.debug(f"R2 config: {self.r2_config}")

    def _determine_comparison_targets(self) -> Dict[str, Any]:
        """
        Determine which versions to compare against for changelog generation.

        Returns:
            Dictionary with:
                'primary': Path to primary comparison target (previous stable)
                'secondary': Path to secondary target (beta if building stable)
                'primary_type': 'stable-to-stable' or 'stable-to-beta'
                'secondary_type': 'beta-to-stable' or None
        """
        current_version, is_current_beta = self._parse_version_with_beta(
            self.fm_version
        )

        result = {
            "primary": None,
            "secondary": None,
            "primary_type": None,
            "secondary_type": None,
        }

        # Check for override first
        if self.previous_version_override:
            override_path = self.base_output_dir / self.previous_version_override
            if override_path.exists() and (override_path / "metadata.json").exists():
                log.info(
                    f"  Using override previous version: {self.previous_version_override}"
                )
                result["primary"] = override_path
                result["primary_type"] = "manual-override"
                return result
            else:
                log.warning(
                    f"  Override version not found: {self.previous_version_override}"
                )
                log.warning("  Falling back to auto-detection")

        # Find previous stable version
        prev_stable = self._find_previous_stable()

        if is_current_beta:
            # Building beta: compare to previous stable
            result["primary"] = prev_stable
            result["primary_type"] = "stable-to-beta"

        else:
            # Building stable: compare to previous stable (PRIMARY)
            result["primary"] = prev_stable
            result["primary_type"] = "stable-to-stable"

            # Also compare to beta (SECONDARY)
            matching_beta = self._find_matching_beta()
            if matching_beta:
                result["secondary"] = matching_beta
                result["secondary_type"] = "beta-to-stable"

        return result

    def _generate_changelog_if_needed(self) -> Optional[Dict[str, Any]]:
        """
        Generate primary and optionally secondary (beta) changelogs.

        Returns:
            Primary changelog dictionary or None if no previous version exists
        """
        import json

        # Check if changelog generation is disabled
        if self.skip_changelog:
            log.info("  Changelog generation skipped (--no-changelog flag)")
            return None

        # Try to download previous version from R2 if configured
        if self.r2_config.get("endpoint") and self.r2_config.get("bucket"):
            self._try_download_previous_from_r2()

        targets = self._determine_comparison_targets()

        if not targets["primary"]:
            log.info("  No previous version found - skipping changelog generation")
            return None

        # Generate PRIMARY changelog (vs stable)
        try:
            log.info(
                f"  Generating PRIMARY changelog: {targets['primary'].name} → {self.fm_version} ({targets['primary_type']})"
            )

            differ = VersionDiffer(targets["primary"], self.output_dir)
            differ.load_catalogues()
            changelog = differ.compare()

            # Add comparison type to changelog
            changelog["comparison_type"] = targets["primary_type"]

            # Save primary changelog
            changelog_path = self.output_dir / "changelog-summary.json"
            with open(changelog_path, "w", encoding="utf-8") as f:
                indent = 2 if self.pretty_json else None
                json.dump(changelog, f, ensure_ascii=False, indent=indent)

            log.info(f"  ✅ Primary changelog saved: {changelog_path}")

            # Generate HTML report
            html_report = differ.generate_html_report(changelog)
            html_path = self.output_dir / "changelog.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_report)

            log.info(f"  ✅ HTML report saved: {html_path}")

            # Store changelog info for metadata (will be added during export)
            self._changelog_metadata = {
                "previous_fm_version": targets["primary"].name,
                "changes_since_previous": changelog["summary"],
                "comparison_type": targets["primary_type"],
            }

            log.info("  ✅ Changelog info prepared for metadata")

        except Exception as e:
            log.error(f"  Failed to generate primary changelog: {e}")
            import traceback

            log.debug(traceback.format_exc())
            return None

        # Generate SECONDARY changelog (beta → stable, if applicable)
        if targets["secondary"]:
            try:
                log.info(
                    f"  Generating SECONDARY changelog: {targets['secondary'].name} → {self.fm_version} ({targets['secondary_type']})"
                )

                beta_differ = VersionDiffer(targets["secondary"], self.output_dir)
                beta_differ.load_catalogues()
                beta_changelog = beta_differ.compare()

                # Add comparison type
                beta_changelog["comparison_type"] = targets["secondary_type"]

                # Save beta changelog
                beta_changelog_path = self.output_dir / "beta-changelog-summary.json"
                with open(beta_changelog_path, "w", encoding="utf-8") as f:
                    indent = 2 if self.pretty_json else None
                    json.dump(beta_changelog, f, ensure_ascii=False, indent=indent)

                log.info(f"  ✅ Beta changelog saved: {beta_changelog_path}")

                # Save detailed beta changes (simplified version for website)
                beta_changes = self._extract_beta_changes(beta_changelog)
                beta_changes_path = self.output_dir / "beta-changes.json"
                with open(beta_changes_path, "w", encoding="utf-8") as f:
                    indent = 2 if self.pretty_json else None
                    json.dump(beta_changes, f, ensure_ascii=False, indent=indent)

                log.info(f"  ✅ Beta changes saved: {beta_changes_path}")

            except Exception as e:
                log.error(f"  Failed to generate beta changelog: {e}")
                import traceback

                log.debug(traceback.format_exc())

        # Return primary changelog for change tracking
        return changelog

    def _apply_change_tracking(self, changelog: Dict[str, Any]) -> None:
        """
        Apply change tracking from changelog to assets.

        This populates change_status, changed_in_version, and previous_* fields
        on all assets based on the primary changelog comparison.

        Args:
            changelog: Primary changelog dictionary from version comparison
        """
        if not changelog:
            return

        changes_by_type = changelog.get("changes_by_type", {})

        # Process CSS Variables (note: changelog uses SINGULAR "css_variable")
        changes = changes_by_type.get("css_variable", {})
        added_names = {c["name"] for c in changes.get("added", [])}
        modified_data = {c["name"]: c for c in changes.get("modified", [])}

        for var in self.css_variables:
            if var.name in added_names:
                var.change_status = "new"
                var.changed_in_version = self.fm_version
            elif var.name in modified_data:
                var.change_status = "modified"
                var.changed_in_version = self.fm_version
                mod = modified_data[var.name]
                if "old_values" in mod:
                    var.previous_values = str(mod["old_values"])
            else:
                var.change_status = "unchanged"

        # Process CSS Classes (note: changelog uses SINGULAR "css_class")
        changes = changes_by_type.get("css_class", {})
        added_names = {c["name"] for c in changes.get("added", [])}
        modified_names = {c["name"] for c in changes.get("modified", [])}

        for cls in self.css_classes:
            if cls.name in added_names:
                cls.change_status = "new"
                cls.changed_in_version = self.fm_version
            elif cls.name in modified_names:
                cls.change_status = "modified"
                cls.changed_in_version = self.fm_version
            else:
                cls.change_status = "unchanged"

        # Process Sprites (note: changelog uses SINGULAR "sprite")
        changes = changes_by_type.get("sprite", {})
        added_names = {c["name"] for c in changes.get("added", [])}
        modified_data = {c["name"]: c for c in changes.get("modified", [])}

        for sprite in self.sprites:
            if sprite.name in added_names:
                sprite.change_status = "new"
                sprite.changed_in_version = self.fm_version
            elif sprite.name in modified_data:
                sprite.change_status = "modified"
                sprite.changed_in_version = self.fm_version
                mod = modified_data[sprite.name]
                if "old_hash" in mod:
                    sprite.previous_content_hash = mod["old_hash"]
            else:
                sprite.change_status = "unchanged"

        # Process Textures (note: changelog uses SINGULAR "texture")
        changes = changes_by_type.get("texture", {})
        added_names = {c["name"] for c in changes.get("added", [])}
        modified_data = {c["name"]: c for c in changes.get("modified", [])}

        for texture in self.textures:
            if texture.name in added_names:
                texture.change_status = "new"
                texture.changed_in_version = self.fm_version
            elif texture.name in modified_data:
                texture.change_status = "modified"
                texture.changed_in_version = self.fm_version
                mod = modified_data[texture.name]
                if "old_hash" in mod:
                    texture.previous_content_hash = mod["old_hash"]
            else:
                texture.change_status = "unchanged"

        # Process Fonts (note: changelog uses SINGULAR "font")
        changes = changes_by_type.get("font", {})
        added_names = {c["name"] for c in changes.get("added", [])}
        modified_names = {c["name"] for c in changes.get("modified", [])}

        for font in self.fonts:
            if font.name in added_names:
                font.change_status = "new"
                font.changed_in_version = self.fm_version
            elif font.name in modified_names:
                font.change_status = "modified"
                font.changed_in_version = self.fm_version
            else:
                font.change_status = "unchanged"

        # Log statistics
        total_new = sum(1 for v in self.css_variables if v.change_status == "new")
        total_new += sum(1 for c in self.css_classes if c.change_status == "new")
        total_new += sum(1 for s in self.sprites if s.change_status == "new")
        total_new += sum(1 for t in self.textures if t.change_status == "new")
        total_new += sum(1 for f in self.fonts if f.change_status == "new")

        total_modified = sum(
            1 for v in self.css_variables if v.change_status == "modified"
        )
        total_modified += sum(
            1 for c in self.css_classes if c.change_status == "modified"
        )
        total_modified += sum(1 for s in self.sprites if s.change_status == "modified")
        total_modified += sum(1 for t in self.textures if t.change_status == "modified")
        total_modified += sum(1 for f in self.fonts if f.change_status == "modified")

        log.info(
            f"  ✅ Applied change tracking: {total_new} new, {total_modified} modified"
        )

    def _extract_beta_changes(self, changelog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract simplified beta changes for website consumption.

        Args:
            changelog: Full changelog dictionary

        Returns:
            Simplified changes dictionary with lists of names by type
        """
        beta_changes = {}

        # Map plural output keys to singular changelog keys
        key_mapping = {
            "sprites": "sprite",
            "textures": "texture",
            "css_variables": "css_variable",
            "css_classes": "css_class",
            "fonts": "font",
        }

        for asset_type in [
            "sprites",
            "textures",
            "css_variables",
            "css_classes",
            "fonts",
        ]:
            # Use singular key to check changelog (generated by version_differ.py)
            changelog_key = key_mapping[asset_type]

            if changelog_key in changelog.get("changes_by_type", {}):
                type_changes = changelog["changes_by_type"][changelog_key]

                # Output uses plural key for website consumption
                beta_changes[asset_type] = {
                    "new": [c["name"] for c in type_changes.get("added", [])],
                    "modified": [c["name"] for c in type_changes.get("modified", [])],
                    "removed": [c["name"] for c in type_changes.get("removed", [])],
                }

        return beta_changes
