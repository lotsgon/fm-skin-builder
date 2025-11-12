#!/usr/bin/env python3
"""
Update latest.json metadata in R2 for auto-updates.

This file is used by:
- Website download page (fetch latest stable/beta)
- Tauri auto-updater (check for updates)
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    import boto3
    from botocore.client import Config
except ImportError:
    print("Error: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


def create_r2_client():
    """Create boto3 S3 client configured for Cloudflare R2."""
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        print("Error: Missing R2 credentials in environment variables")
        sys.exit(1)

    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )
    return s3


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_artifact_info(
    artifacts_dir: Path, version: str, is_beta: bool = False
) -> Dict[str, Any]:
    """
    Extract artifact information from build artifacts.

    Returns a dict with platform keys containing:
    - Tauri updater info (url, signature for .tar.gz/.zip archives)
    - User installer info (download links for .dmg, .exe, .AppImage, .deb)
    """
    platforms = {}

    # Base URL for downloads
    base_path = "beta" if is_beta else "releases"
    base_url = f"https://releases.fm-skin-builder.com/{base_path}/{version}"

    # Find all artifacts
    for root, _, files in os.walk(artifacts_dir):
        for file in files:
            file_path = Path(root) / file
            file_size = file_path.stat().st_size

            # Determine platform and architecture from filename
            platform_key = None
            is_updater = False
            is_installer = False
            installer_format = None

            # macOS updater files (.app.tar.gz)
            if file.endswith(".app.tar.gz") and not file.endswith(".sig"):
                is_updater = True
                if "aarch64" in file.lower() or "arm64" in file.lower():
                    platform_key = "darwin-aarch64"
                else:
                    platform_key = "darwin-x86_64"

            # macOS installers (.dmg)
            elif file.endswith(".dmg"):
                is_installer = True
                installer_format = "dmg"
                if "aarch64" in file.lower() or "arm64" in file.lower():
                    platform_key = "darwin-aarch64"
                else:
                    platform_key = "darwin-x86_64"

            # Windows updater files (.msi.zip)
            elif file.endswith(".msi.zip") and not file.endswith(".sig"):
                is_updater = True
                platform_key = "windows-x86_64"

            # Windows installers (.exe, .msi)
            elif file.endswith(".exe") or (
                file.endswith(".msi") and not file.endswith(".msi.zip")
            ):
                is_installer = True
                installer_format = "exe" if file.endswith(".exe") else "msi"
                platform_key = "windows-x86_64"

            # Linux updater files (.AppImage.tar.gz)
            elif file.endswith(".AppImage.tar.gz") and not file.endswith(".sig"):
                is_updater = True
                platform_key = "linux-x86_64"

            # Linux installers (.AppImage, .deb)
            elif file.endswith(".AppImage") and not file.endswith(".tar.gz"):
                is_installer = True
                installer_format = "AppImage"
                platform_key = "linux-x86_64"
            elif file.endswith(".deb"):
                is_installer = True
                installer_format = "deb"
                platform_key = "linux-x86_64"

            # Initialize platform entry if needed
            if platform_key and platform_key not in platforms:
                platforms[platform_key] = {"installers": []}

            # Add updater info (for Tauri)
            if is_updater and platform_key:
                sig_file = file_path.parent / f"{file}.sig"
                if sig_file.exists():
                    platforms[platform_key]["url"] = f"{base_url}/{file}"
                    platforms[platform_key]["signature"] = sig_file.read_text().strip()

            # Add installer info (for website downloads)
            if is_installer and platform_key and installer_format:
                platforms[platform_key]["installers"].append(
                    {
                        "url": f"{base_url}/{file}",
                        "format": installer_format,
                        "size": file_size,
                    }
                )

    return platforms


def get_current_metadata(s3, bucket: str) -> Dict[str, Any]:
    """Get current latest.json from R2, or return default structure."""
    try:
        response = s3.get_object(Bucket=bucket, Key="latest.json")
        return json.loads(response["Body"].read().decode("utf-8"))
    except Exception:
        # File doesn't exist yet, return default
        return {
            "stable": None,
            "beta": None,
            "last_updated": None,
        }


def update_metadata(
    artifacts_dir: Path,
    bucket: str,
    version: str,
    is_beta: bool,
    release_notes: str = "",
) -> None:
    """Update latest.json in R2 with new release info."""
    s3 = create_r2_client()

    print(f"Updating metadata for version: {version}")
    print(f"Type: {'Beta' if is_beta else 'Stable'}")

    # Get current metadata
    metadata = get_current_metadata(s3, bucket)

    # Get artifact information
    platforms = get_artifact_info(artifacts_dir, version, is_beta)

    # Create release entry
    release_entry = {
        "version": version,
        "date": datetime.utcnow().isoformat() + "Z",
        "platforms": platforms,
        "notes": release_notes,
    }

    # Update appropriate field
    if is_beta:
        metadata["beta"] = release_entry
    else:
        metadata["stable"] = release_entry

    metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Upload updated metadata
    print("\nUploading latest.json...")
    s3.put_object(
        Bucket=bucket,
        Key="latest.json",
        Body=json.dumps(metadata, indent=2),
        ContentType="application/json",
        CacheControl="max-age=300",  # Cache for 5 minutes
    )

    print("✅ Metadata updated successfully")
    print("\nCurrent releases:")
    if metadata["stable"]:
        print(f"  Stable: {metadata['stable']['version']}")
    else:
        print("  Stable: None")

    if metadata["beta"]:
        print(f"  Beta: {metadata['beta']['version']}")
    else:
        print("  Beta: None")

    # Also create version-specific metadata for Tauri updater
    print(f"\nCreating version-specific metadata: {version}.json")
    version_metadata = {
        "version": version,
        "pub_date": release_entry["date"],
        "platforms": platforms,
        "notes": release_notes,
    }

    s3.put_object(
        Bucket=bucket,
        Key=f"metadata/{version}.json",
        Body=json.dumps(version_metadata, indent=2),
        ContentType="application/json",
    )

    print(f"✅ Version metadata uploaded: metadata/{version}.json")


def main():
    parser = argparse.ArgumentParser(description="Update latest.json metadata in R2")
    parser.add_argument(
        "--artifacts-dir",
        required=True,
        type=Path,
        help="Directory containing build artifacts",
    )
    parser.add_argument("--bucket", required=True, help="R2 bucket name")
    parser.add_argument("--version", required=True, help="Version string")
    parser.add_argument("--beta", action="store_true", help="This is a beta release")
    parser.add_argument("--notes", default="", help="Release notes (optional)")

    args = parser.parse_args()

    if not args.artifacts_dir.exists():
        print(f"Error: Artifacts directory not found: {args.artifacts_dir}")
        sys.exit(1)

    update_metadata(
        artifacts_dir=args.artifacts_dir,
        bucket=args.bucket,
        version=args.version,
        is_beta=args.beta,
        release_notes=args.notes,
    )


if __name__ == "__main__":
    main()
