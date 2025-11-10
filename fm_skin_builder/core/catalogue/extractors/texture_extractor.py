"""
Texture Extractor

Extracts texture assets (backgrounds, UI textures) from Unity bundles.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import UnityPy

from .base import BaseAssetExtractor
from ...logger import get_logger

log = get_logger(__name__)


class TextureExtractor(BaseAssetExtractor):
    """Extracts texture assets from bundles."""

    def extract_from_bundle(self, bundle_path: Path) -> List[Dict[str, Any]]:
        """
        Extract textures from a bundle.

        Args:
            bundle_path: Path to .bundle file

        Returns:
            List of texture data dictionaries
        """
        import gc
        import sys

        textures = []

        try:
            log.info(f"    Loading bundle: {bundle_path.name}")
            sys.stdout.flush()
            env = UnityPy.load(str(bundle_path))
            log.info(f"    Bundle loaded successfully")
            sys.stdout.flush()
        except Exception as e:
            # If we can't load the bundle, return empty list
            log.warning(f"    Failed to load bundle: {e}")
            return textures

        bundle_name = bundle_path.name

        try:
            log.info(f"    Iterating through objects...")
            sys.stdout.flush()

            for obj in env.objects:
                if obj.type.name != "Texture2D":
                    continue

                try:
                    log.info(f"    Reading Texture2D object...")
                    sys.stdout.flush()
                    data = obj.read()
                    log.info(f"    Object read successfully")
                    sys.stdout.flush()
                except Exception as e:
                    log.warning(f"    Failed to read object: {e}")
                    continue

                name = self._get_asset_name(data)
                if not name:
                    continue

                try:
                    texture_data = self._extract_texture_data(data, bundle_path)
                    if texture_data:
                        textures.append(texture_data)
                except Exception:
                    # Skip problematic textures
                    continue
        finally:
            # Clean up UnityPy environment
            try:
                del env
            except:
                pass
            gc.collect()

        return textures

    def _extract_texture_data(
        self, texture_obj: Any, bundle_path: Path
    ) -> Optional[Dict[str, Any]]:
        """
        Extract texture data and image.

        Args:
            texture_obj: Unity texture object
            bundle_path: Path to the bundle file

        Returns:
            Dictionary with texture metadata and image data
        """
        import sys

        bundle_name = bundle_path.name

        log.info(f"    Getting asset name...")
        sys.stdout.flush()
        name = self._get_asset_name(texture_obj)
        log.info(f"    Asset name: {name}")
        sys.stdout.flush()

        if not name:
            return None

        # Get dimensions
        log.info(f"    Getting width...")
        sys.stdout.flush()
        width = getattr(texture_obj, "m_Width", 0)
        log.info(f"    Width: {width}")
        sys.stdout.flush()

        log.info(f"    Getting height...")
        sys.stdout.flush()
        height = getattr(texture_obj, "m_Height", 0)
        log.info(f"    Height: {height}")
        sys.stdout.flush()

        # Classify texture type based on name patterns
        texture_type = self._classify_texture_type(name)

        # Extract image data
        image_data = None
        try:
            # NOTE: DO NOT use hasattr(texture_obj, 'image') as it triggers property
            # access which causes segfaults on macOS. Just try to access directly.

            # Check texture format - some formats cause segfaults
            log.info(f"    Getting texture format for {name}...")
            sys.stdout.flush()
            texture_format = getattr(texture_obj, "m_TextureFormat", None)
            log.info(f"    Texture format retrieved: {texture_format}")
            sys.stdout.flush()

            texture_format_name = str(texture_format) if texture_format is not None else "unknown"

            # Log texture details for debugging - this helps identify crashes
            log.info(f"    Processing texture: {name} (format={texture_format_name}, {width}x{height})")
            sys.stdout.flush()

            # Skip problematic texture formats that cause segfaults
            # These are known to crash UnityPy on certain platforms
            # Common problematic formats that cause C-level crashes:
            # - ASTC_4x4, ASTC_5x5, ASTC_6x6, ASTC_8x8, ASTC_10x10, ASTC_12x12 (ASTC compressed formats)
            # - ETC_RGB4, ETC2_RGB, ETC2_RGBA (without proper decoders on macOS)
            # - BC7 (on some older systems without decoder support)
            # - PVRTC formats (platform-specific issues)
            #
            # Unity TextureFormat enum values for reference:
            # ASTC formats: typically 48-53
            # ETC formats: typically 34, 45-47
            # BC7: 26
            # PVRTC formats: 30-33
            problematic_formats = [
                # ASTC formats (enum values 48-53)
                48, 49, 50, 51, 52, 53,
                # ETC formats (enum values 34, 45-47)
                34, 45, 46, 47,
                # BC7 (enum value 26)
                26,
                # PVRTC formats (enum values 30-33)
                30, 31, 32, 33,
            ]

            # Also check by name if format is an enum
            if hasattr(texture_format, 'name'):
                format_name = texture_format.name
                if any(problematic in format_name for problematic in ['ASTC', 'ETC', 'PVRTC', 'BC7']):
                    log.warning(f"    Skipping texture {name} with potentially problematic format {format_name}")
                    return {
                        "name": name,
                        "bundle": bundle_name,
                        "type": texture_type,
                        "width": width,
                        "height": height,
                        "image_data": None,
                        **self._create_default_status(),
                    }

            if texture_format in problematic_formats:
                log.warning(f"    Skipping texture {name} with problematic format {texture_format}")
                # Skip image extraction but keep metadata
                return {
                    "name": name,
                    "bundle": bundle_name,
                    "type": texture_type,
                    "width": width,
                    "height": height,
                    "image_data": None,
                    **self._create_default_status(),
                }

            # Access image - this is where segfaults often occur
            log.info(f"    Accessing .image property for {name}...")
            sys.stdout.flush()

            # On macOS, formats 28 (DXT1) and 29 (DXT5) cause segfaults in UnityPy's decoder
            # Use texture2ddecoder as a fallback on macOS
            import platform
            use_fallback_decoder = platform.system() == 'Darwin' and texture_format in [28, 29]

            if use_fallback_decoder:
                # On macOS, use subprocess isolation to prevent crashes
                format_name = "DXT1" if texture_format == 28 else "DXT5"
                log.info(f"    Using subprocess isolation for {format_name} (format {texture_format}) on macOS")
                sys.stdout.flush()

                from multiprocessing import Process, Queue
                import io

                def extract_in_subprocess(bundle_path_str, tex_name, queue):
                    """Extract texture in isolated subprocess - if it crashes, only subprocess dies."""
                    try:
                        import UnityPy
                        from PIL import Image as PILImage
                        import io

                        # Reload bundle in subprocess
                        env = UnityPy.load(bundle_path_str)
                        for obj in env.objects:
                            if obj.type.name != "Texture2D":
                                continue
                            data = obj.read()
                            obj_name = getattr(data, "m_Name", None) or getattr(data, "name", None)
                            if obj_name == tex_name:
                                # Try to get image (may crash subprocess)
                                img = data.image
                                if img:
                                    buf = io.BytesIO()
                                    # Pre-downsample if needed
                                    if img.width > 2048 or img.height > 2048:
                                        img.thumbnail((2048, 2048), PILImage.Resampling.LANCZOS)
                                    img.save(buf, format='PNG')
                                    queue.put(('success', buf.getvalue()))
                                else:
                                    queue.put(('empty', None))
                                return
                        queue.put(('notfound', None))
                    except Exception as e:
                        queue.put(('error', str(e)))

                queue = Queue()
                process = Process(target=extract_in_subprocess, args=(str(bundle_path), name, queue))
                process.start()
                process.join(timeout=30)  # 30 second timeout

                if process.is_alive():
                    # Process timed out
                    process.terminate()
                    process.join()
                    log.warning(f"    Subprocess timeout for {name}")
                    return {
                        "name": name,
                        "bundle": bundle_name,
                        "type": texture_type,
                        "width": width,
                        "height": height,
                        "image_data": None,
                        **self._create_default_status(),
                    }

                if process.exitcode != 0:
                    # Process crashed (segfault)
                    log.warning(f"    Subprocess crashed (segfault) for {name} - skipping image")
                    return {
                        "name": name,
                        "bundle": bundle_name,
                        "type": texture_type,
                        "width": width,
                        "height": height,
                        "image_data": None,
                        **self._create_default_status(),
                    }

                # Get result from queue
                try:
                    result = queue.get_nowait()
                    if result[0] == 'success':
                        image_data = result[1]
                        log.info(f"    Success! Image extracted via subprocess")
                        sys.stdout.flush()
                    elif result[0] == 'notfound':
                        log.warning(f"    Texture not found in subprocess reload")
                        return {
                            "name": name,
                            "bundle": bundle_name,
                            "type": texture_type,
                            "width": width,
                            "height": height,
                            "image_data": None,
                            **self._create_default_status(),
                        }
                    else:
                        log.warning(f"    Subprocess error: {result[1]}")
                        return {
                            "name": name,
                            "bundle": bundle_name,
                            "type": texture_type,
                            "width": width,
                            "height": height,
                            "image_data": None,
                            **self._create_default_status(),
                        }
                except Exception as e:
                    log.warning(f"    Failed to get result from subprocess: {e}")
                    return {
                        "name": name,
                        "bundle": bundle_name,
                        "type": texture_type,
                        "width": width,
                        "height": height,
                        "image_data": None,
                        **self._create_default_status(),
                    }

                # Continue with the image_data extracted by subprocess
                # image_data already set by subprocess
            else:
                # Use UnityPy's built-in decoder (works fine on Linux)
                image = texture_obj.image
                log.info(f"    Image accessed successfully")
                sys.stdout.flush()

                if image:
                    # For large images, convert to thumbnail immediately to save memory
                    # Don't store full 4K+ images in memory
                    from PIL import Image
                    import io

                    # Create a copy to avoid modifying original
                    img_copy = image.copy()

                    # If image is very large, create thumbnail immediately
                    if img_copy.width > 2048 or img_copy.height > 2048:
                        # Create thumbnail at 2048x2048 max (will be thumbnailed again to 256x256 later)
                        img_copy.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

                    # Convert to PNG bytes
                    buf = io.BytesIO()
                    img_copy.save(buf, format='PNG')
                    image_data = buf.getvalue()

                    # Clean up
                    del img_copy
                    del buf
        except Exception as e:
            # Image extraction failed, continue without image data
            # Don't fail the entire extraction for one bad image
            pass

        return {
            "name": name,
            "bundle": bundle_name,
            "type": texture_type,
            "width": width,
            "height": height,
            "image_data": image_data,
            **self._create_default_status(),
        }

    def _decode_dxt_texture(self, texture_obj: Any, texture_format: int, width: int, height: int):
        """
        Decode DXT compressed texture using texture2ddecoder.

        This is a fallback decoder for macOS where UnityPy's decoder crashes.

        Args:
            texture_obj: Unity texture object
            texture_format: Format enum (28=DXT1, 29=DXT5)
            width: Texture width
            height: Texture height

        Returns:
            PIL Image or None
        """
        try:
            import texture2ddecoder
            from PIL import Image
            import numpy as np

            # Debug: log available attributes
            attrs = [attr for attr in dir(texture_obj) if not attr.startswith('_')]
            log.debug(f"    Available attributes: {attrs[:20]}")  # First 20 to avoid spam

            # Get raw compressed data from Unity texture
            # Try various property names that might contain the data
            raw_data = None

            # Try image_data property
            if hasattr(texture_obj, 'image_data'):
                raw_data = texture_obj.image_data
                log.debug(f"    Found image_data: {type(raw_data)}, len={len(raw_data) if raw_data else 0}")

            # Try m_ImageData
            if not raw_data and hasattr(texture_obj, 'm_ImageData'):
                raw_data = texture_obj.m_ImageData
                log.debug(f"    Found m_ImageData: {type(raw_data)}, len={len(raw_data) if raw_data else 0}")

            # Try m_Data
            if not raw_data and hasattr(texture_obj, 'm_Data'):
                raw_data = texture_obj.m_Data
                log.debug(f"    Found m_Data: {type(raw_data)}, len={len(raw_data) if raw_data else 0}")

            # Try get_image_data() method if it exists
            if not raw_data and hasattr(texture_obj, 'get_image_data'):
                raw_data = texture_obj.get_image_data()
                log.debug(f"    Found get_image_data(): {type(raw_data)}, len={len(raw_data) if raw_data else 0}")

            if not raw_data:
                log.warning(f"    No raw texture data available in any known property")
                return None

            # Decode based on format
            if texture_format == 28:  # DXT1/BC1
                decoded = texture2ddecoder.decode_bc1(raw_data, width, height)
            elif texture_format == 29:  # DXT5/BC3
                decoded = texture2ddecoder.decode_bc3(raw_data, width, height)
            else:
                log.warning(f"    Unsupported format for texture2ddecoder: {texture_format}")
                return None

            # Convert decoded bytes to PIL Image
            # texture2ddecoder returns raw RGBA bytes
            img = Image.frombytes("RGBA", (width, height), decoded, "raw", "BGRA")

            return img

        except ImportError:
            log.warning(f"    texture2ddecoder not installed, cannot decode DXT textures on macOS")
            return None
        except Exception as e:
            log.warning(f"    Error decoding DXT texture: {e}")
            import traceback
            log.debug(f"    Traceback: {traceback.format_exc()}")
            return None

    def _classify_texture_type(self, name: str) -> str:
        """
        Classify texture type based on name patterns.

        Args:
            name: Texture name

        Returns:
            Type string: 'background', 'icon', or 'texture'
        """
        name_lower = name.lower()

        if any(pattern in name_lower for pattern in ["bg_", "background", "backdrop"]):
            return "background"
        elif any(pattern in name_lower for pattern in ["icon_", "ico_", "symbol"]):
            return "icon"
        else:
            return "texture"
