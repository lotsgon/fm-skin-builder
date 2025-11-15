"""
R2 Downloader for Catalogue Versions

Downloads previous catalogue versions from Cloudflare R2 for comparison.
Only downloads JSON metadata files, not thumbnails.
"""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Try to import boto3 for R2 access
try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    log.warning("boto3 not available - R2 download functionality disabled")


class R2Downloader:
    """Downloads catalogue versions from Cloudflare R2."""

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize R2 downloader.

        Args:
            endpoint_url: R2 endpoint URL (e.g., 'https://account.r2.cloudflarestorage.com')
            bucket: R2 bucket name
            access_key: R2 access key ID (falls back to R2_ACCESS_KEY env var)
            secret_key: R2 secret access key (falls back to R2_SECRET_KEY env var)
        """
        if not BOTO3_AVAILABLE:
            raise RuntimeError(
                "boto3 is required for R2 downloads. Install with: pip install boto3"
            )

        self.endpoint_url = endpoint_url
        self.bucket = bucket

        # Get credentials from args or environment
        self.access_key = access_key or os.environ.get("R2_ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("R2_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "R2 credentials required. Provide --r2-access-key and --r2-secret-key "
                "or set R2_ACCESS_KEY and R2_SECRET_KEY environment variables."
            )

        # Initialize S3 client (R2 uses S3-compatible API)
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto",  # R2 uses 'auto' region
        )

    def download_version(
        self, fm_version: str, output_dir: Path, base_path: str = ""
    ) -> bool:
        """
        Download a specific catalogue version from R2.

        Downloads only JSON metadata files, not thumbnails.

        Args:
            fm_version: FM version to download (e.g., '2026.4.0')
            output_dir: Local directory to download to
            base_path: Base path in R2 bucket (e.g., 'catalogues/')

        Returns:
            True if download succeeded, False otherwise
        """
        version_dir = output_dir / fm_version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Files to download (JSON metadata only, no thumbnails)
        files_to_download = [
            "metadata.json",
            "sprites.json",
            "textures.json",
            "css-variables.json",
            "css-classes.json",
            "fonts.json",
            "search-index.json",
            "changelog-summary.json",  # May not exist for first version
            "beta-changelog-summary.json",  # May not exist
            "beta-changes.json",  # May not exist
            "changelog.html",  # May not exist
        ]

        downloaded_count = 0
        required_files = [
            "metadata.json",
            "sprites.json",
            "textures.json",
            "css-variables.json",
            "css-classes.json",
            "fonts.json",
        ]

        for filename in files_to_download:
            r2_key = f"{base_path}{fm_version}/{filename}"
            local_path = version_dir / filename

            try:
                log.info(f"  Downloading {r2_key}...")
                self.s3_client.download_file(self.bucket, r2_key, str(local_path))
                downloaded_count += 1
                log.info(f"  ✅ Downloaded: {filename}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "404" or error_code == "NoSuchKey":
                    if filename in required_files:
                        log.error(f"  ❌ Required file not found: {filename}")
                        return False
                    else:
                        log.debug(f"  Optional file not found: {filename}")
                else:
                    log.error(f"  ❌ Error downloading {filename}: {e}")
                    if filename in required_files:
                        return False
            except Exception as e:
                log.error(f"  ❌ Unexpected error downloading {filename}: {e}")
                if filename in required_files:
                    return False

        if downloaded_count == 0:
            log.error(f"  ❌ No files downloaded for version {fm_version}")
            return False

        log.info(f"  ✅ Downloaded {downloaded_count} files for version {fm_version}")
        return True

    def list_versions(self, base_path: str = "") -> list[str]:
        """
        List all available catalogue versions in R2.

        Args:
            base_path: Base path in R2 bucket (e.g., 'catalogues/')

        Returns:
            List of version strings found in R2
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=base_path,
                Delimiter="/",
            )

            versions = []
            for prefix in response.get("CommonPrefixes", []):
                # Extract version from prefix (e.g., 'catalogues/2026.4.0/' -> '2026.4.0')
                version = prefix["Prefix"].rstrip("/").split("/")[-1]
                versions.append(version)

            return sorted(versions)
        except Exception as e:
            log.error(f"Error listing R2 versions: {e}")
            return []

    def version_exists(self, fm_version: str, base_path: str = "") -> bool:
        """
        Check if a version exists in R2.

        Args:
            fm_version: FM version to check
            base_path: Base path in R2 bucket

        Returns:
            True if version exists (metadata.json is present)
        """
        r2_key = f"{base_path}{fm_version}/metadata.json"
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=r2_key)
            return True
        except ClientError:
            return False
