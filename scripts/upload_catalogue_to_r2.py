#!/usr/bin/env python3
"""
Upload generated catalogue to R2 bucket.
"""

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config


def upload_catalogue(catalogue_dir: Path, fm_version: str, catalogue_version: str):
    """
    Upload catalogue to R2 bucket.

    Args:
        catalogue_dir: Local directory containing catalogue files
        fm_version: FM version (e.g., "2025.0.0")
        catalogue_version: Catalogue version number
    """
    # Get R2 credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_CATALOGUE_BUCKET", "fm-asset-catalogue")

    if not all([account_id, access_key, secret_key]):
        print("Error: R2 credentials not found in environment variables")
        print("Required: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
        sys.exit(1)

    if not catalogue_dir.exists():
        print(f"Error: Catalogue directory not found: {catalogue_dir}")
        sys.exit(1)

    # Initialize R2 client (uses S3 API)
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    print(f"Uploading catalogue to R2: {bucket_name}")
    print(f"  FM Version: {fm_version}")
    print(f"  Catalogue Version: {catalogue_version}")

    # R2 prefix for this catalogue version
    prefix = f"{fm_version}/v{catalogue_version}"

    # Upload all files recursively
    file_count = 0
    total_size = 0

    for file_path in catalogue_dir.rglob("*"):
        if file_path.is_dir():
            continue

        # Calculate relative path for R2 key
        relative_path = file_path.relative_to(catalogue_dir)
        r2_key = f"{prefix}/{relative_path}"

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        # Special handling for specific file types
        if file_path.suffix == ".json":
            content_type = "application/json"
        elif file_path.suffix == ".webp":
            content_type = "image/webp"

        print(f"  Uploading: {relative_path} ({file_path.stat().st_size / 1024:.1f} KB)")

        extra_args = {
            "ContentType": content_type,
        }

        # Set cache control for static assets
        if file_path.suffix in [".webp", ".json"]:
            extra_args["CacheControl"] = "public, max-age=31536000"  # 1 year

        try:
            s3.upload_file(
                str(file_path),
                bucket_name,
                r2_key,
                ExtraArgs=extra_args,
            )
            file_count += 1
            total_size += file_path.stat().st_size
        except Exception as e:
            print(f"  ❌ Error uploading {relative_path}: {e}")
            continue

    print(f"\n✅ Uploaded {file_count} files ({total_size / 1024 / 1024:.1f} MB)")
    print(f"   R2 Location: {bucket_name}/{prefix}/")

    # If R2 bucket has public access, print the public URL
    print(f"\n   Public URL: https://your-r2-domain.com/{prefix}/metadata.json")


def main():
    parser = argparse.ArgumentParser(description="Upload catalogue to R2")
    parser.add_argument(
        "--catalogue-dir",
        required=True,
        type=Path,
        help="Directory containing catalogue files",
    )
    parser.add_argument(
        "--fm-version",
        required=True,
        help="FM version (e.g., 2025.0.0)",
    )
    parser.add_argument(
        "--catalogue-version",
        required=True,
        help="Catalogue version number",
    )

    args = parser.parse_args()
    upload_catalogue(args.catalogue_dir, args.fm_version, args.catalogue_version)


if __name__ == "__main__":
    main()
