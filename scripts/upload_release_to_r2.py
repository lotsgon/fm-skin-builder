#!/usr/bin/env python3
"""
Upload release artifacts to Cloudflare R2.

This script uploads built application artifacts to R2 for distribution.
Supports both production releases (from tags) and beta builds (from beta branch).
"""

import argparse
import os
import sys
from pathlib import Path

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
        print("Required: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
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


def upload_artifacts(
    artifacts_dir: Path,
    bucket: str,
    version: str,
    beta: bool = False,
) -> None:
    """
    Upload release artifacts to R2.

    Args:
        artifacts_dir: Directory containing build artifacts
        bucket: R2 bucket name
        version: Version string (e.g., "0.1.0" or "0.1.0-beta.abc123")
        beta: If True, upload to /beta/ path; otherwise /releases/
    """
    s3 = create_r2_client()

    # Determine base path
    base_path = "beta" if beta else "releases"
    r2_prefix = f"{base_path}/{version}"

    print("Uploading artifacts to R2:")
    print(f"  Bucket: {bucket}")
    print(f"  Path: {r2_prefix}/")
    print(f"  Type: {'Beta Build' if beta else 'Release'}")
    print()

    # Find all artifact files
    artifact_files = []
    for root, dirs, files in os.walk(artifacts_dir):
        # Skip backend artifacts (already bundled in apps)
        if "backend-" in Path(root).name:
            continue

        for file in files:
            file_path = Path(root) / file
            # Only upload actual release files (user installers + updater files)
            if (
                file_path.suffix in [
                    ".dmg",      # macOS installer
                    ".exe",      # Windows NSIS installer
                    ".msi",      # Windows MSI installer
                    ".deb",      # Linux Debian package
                    ".AppImage", # Linux AppImage
                    ".sig",      # Tauri updater signature files
                    ".zip",      # Windows updater archive
                ]
                or file_path.name.endswith(".tar.gz")  # macOS/Linux updater archives
            ):
                artifact_files.append(file_path)

    if not artifact_files:
        print("Warning: No artifacts found to upload")
        return

    # Upload each file
    uploaded = 0
    for file_path in artifact_files:
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Create R2 key
        r2_key = f"{r2_prefix}/{file_path.name}"

        print(f"Uploading {file_path.name} ({file_size_mb:.2f} MB)...")

        try:
            s3.upload_file(
                str(file_path),
                bucket,
                r2_key,
                ExtraArgs={
                    "ContentType": get_content_type(file_path),
                    "Metadata": {
                        "version": version,
                        "build-type": "beta" if beta else "release",
                    },
                },
            )
            print(f"  ✓ Uploaded to {r2_key}")
            uploaded += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            sys.exit(1)

    print()
    print(f"✅ Successfully uploaded {uploaded} artifacts to R2")
    print(f"   URL: https://{bucket}/{r2_prefix}/")


def get_content_type(file_path: Path) -> str:
    """Get appropriate content type for file."""
    # Handle .tar.gz specially since it has two extensions
    if file_path.name.endswith(".tar.gz"):
        return "application/gzip"

    suffix = file_path.suffix.lower()
    content_types = {
        ".dmg": "application/x-apple-diskimage",
        ".exe": "application/x-msdownload",
        ".msi": "application/x-msi",
        ".deb": "application/vnd.debian.binary-package",
        ".AppImage": "application/x-executable",
        ".zip": "application/zip",
        ".sig": "application/octet-stream",  # Tauri signature file
    }
    return content_types.get(suffix, "application/octet-stream")


def main():
    parser = argparse.ArgumentParser(
        description="Upload release artifacts to Cloudflare R2"
    )
    parser.add_argument(
        "--artifacts-dir",
        required=True,
        type=Path,
        help="Directory containing build artifacts",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version string (e.g., 0.1.0 or 0.1.0-beta.abc123)",
    )
    parser.add_argument("--bucket", required=True, help="R2 bucket name")
    parser.add_argument(
        "--beta",
        action="store_true",
        help="Upload to /beta/ path instead of /releases/",
    )

    args = parser.parse_args()

    if not args.artifacts_dir.exists():
        print(f"Error: Artifacts directory not found: {args.artifacts_dir}")
        sys.exit(1)

    upload_artifacts(
        artifacts_dir=args.artifacts_dir,
        bucket=args.bucket,
        version=args.version,
        beta=args.beta,
    )


if __name__ == "__main__":
    main()
