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
from typing import Dict, Any, List

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


def get_artifact_info(artifacts_dir: Path, version: str) -> Dict[str, Any]:
    """Extract artifact information from build artifacts."""
    platforms = {}

    # Map file extensions to platform info
    platform_map = {
        ".AppImage": {"platform": "linux", "arch": "x86_64"},
        ".deb": {"platform": "linux", "arch": "x86_64", "format": "deb"},
        ".msi": {"platform": "windows", "arch": "x86_64"},
        ".exe": {"platform": "windows", "arch": "x86_64", "format": "nsis"},
    }

    # Find all artifacts
    for root, _, files in os.walk(artifacts_dir):
        for file in files:
            file_path = Path(root) / file

            # Skip signature files and other non-installer files
            if file.endswith(".sig") or file.endswith(".blockmap") or file.endswith(".yml"):
                continue

            # Check file extension
            for ext, info in platform_map.items():
                if file.endswith(ext):
                    # Calculate hash
                    file_hash = calculate_file_hash(file_path)
                    file_size = file_path.stat().st_size

                    # Determine platform key
                    platform = info["platform"]
                    arch = info["arch"]
                    format_type = info.get("format", ext.lstrip("."))

                    # Handle macOS special cases
                    if file.endswith(".dmg"):
                        if "arm64" in file.lower() or "aarch64" in file.lower():
                            arch = "aarch64"
                            platform = "darwin"
                        elif "intel" in file.lower() or "x86_64" in file.lower():
                            arch = "x86_64"
                            platform = "darwin"
                        format_type = "dmg"

                    # Create platform entry
                    key = f"{platform}-{arch}"
                    if key not in platforms:
                        platforms[key] = []

                    platforms[key].append(
                        {
                            "url": f"https://releases.fm-skin-builder.com/{'beta' if '-beta' in version else 'releases'}/{version}/{file}",
                            "signature": file_hash,
                            "format": format_type,
                            "size": file_size,
                        }
                    )

    return platforms


def get_current_metadata(s3, bucket: str) -> Dict[str, Any]:
    """Get current releases.json from R2, or return default structure."""
    try:
        response = s3.get_object(Bucket=bucket, Key="releases.json")
        data = json.loads(response["Body"].read().decode("utf-8"))
        print("✅ Found existing releases.json")
        return data
    except s3.exceptions.NoSuchKey:
        print("ℹ️  releases.json not found, creating new structure")
        return {
            "stable": None,
            "beta": None,
            "last_updated": None,
            "all_releases": [],
        }
    except Exception as e:
        print(f"⚠️  Error reading releases.json: {e}")
        print("ℹ️  Using default structure")
        return {
            "stable": None,
            "beta": None,
            "last_updated": None,
            "all_releases": [],
        }


def update_metadata(
    artifacts_dir: Path,
    bucket: str,
    version: str,
    is_beta: bool,
    release_notes: str = "",
) -> None:
    """Update latest.json and releases.json in R2 with new release info."""
    s3 = create_r2_client()

    print(f"Updating metadata for version: {version}")
    print(f"Type: {'Beta' if is_beta else 'Stable'}")

    # Get current releases.json
    releases = get_current_metadata(s3, bucket)

    # Get artifact information
    platforms = get_artifact_info(artifacts_dir, version)

    # Create release entry
    release_entry = {
        "version": version,
        "date": datetime.utcnow().isoformat() + "Z",
        "platforms": platforms,
        "notes": release_notes,
    }

    # Update appropriate field in releases
    if is_beta:
        releases["beta"] = release_entry
    else:
        releases["stable"] = release_entry

    releases["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Add to all_releases if not already present
    if "all_releases" not in releases:
        releases["all_releases"] = []

    # Check if this version is already in all_releases
    existing_versions = [r.get("version") for r in releases["all_releases"]]
    if version not in existing_versions:
        releases["all_releases"].append(release_entry)

    # Upload releases.json
    print("\nUploading releases.json...")
    try:
        s3.put_object(
            Bucket=bucket,
            Key="releases.json",
            Body=json.dumps(releases, indent=2),
            ContentType="application/json",
            CacheControl="max-age=300",  # Cache for 5 minutes
        )
        print("✅ releases.json uploaded successfully")
    except Exception as e:
        print(f"❌ Failed to upload releases.json: {e}")
        sys.exit(1)

    # Upload latest.json (stable) or latest-beta.json (beta)
    latest_key = "latest-beta.json" if is_beta else "latest.json"
    latest_metadata = {
        "version": version,
        "pub_date": release_entry["date"],
        "platforms": platforms,
        "notes": release_notes,
    }

    print(f"Uploading {latest_key}...")
    try:
        s3.put_object(
            Bucket=bucket,
            Key=latest_key,
            Body=json.dumps(latest_metadata, indent=2),
            ContentType="application/json",
            CacheControl="max-age=300",
        )
        print(f"✅ {latest_key} uploaded successfully")
    except Exception as e:
        print(f"❌ Failed to upload {latest_key}: {e}")
        sys.exit(1)

    print("✅ Metadata updated successfully")
    print(f"\nCurrent releases:")
    stable_info = releases.get("stable")
    if stable_info:
        print(f"  Stable: {stable_info.get('version', 'unknown')}")
    else:
        print("  Stable: None")

    beta_info = releases.get("beta")
    if beta_info:
        print(f"  Beta: {beta_info.get('version', 'unknown')}")
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

    try:
        s3.put_object(
            Bucket=bucket,
            Key=f"metadata/{version}.json",
            Body=json.dumps(version_metadata, indent=2),
            ContentType="application/json",
        )
        print(f"✅ Version metadata uploaded: metadata/{version}.json")
    except Exception as e:
        print(f"❌ Failed to upload metadata/{version}.json: {e}")
        # Don't exit here as this is not critical for the main functionality


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
