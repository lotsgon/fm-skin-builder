#!/usr/bin/env python3
"""
Download FM bundles from R2 bucket for catalogue building.
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config


def download_bundles(prefix: str, output_dir: Path):
    """
    Download bundles from R2 bucket.

    Args:
        prefix: R2 prefix/folder containing bundles
        output_dir: Local directory to save bundles
    """
    # Get R2 credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    bucket_name = os.getenv("R2_BUNDLES_BUCKET", "fm-bundles")

    # Support new R2_API_KEY format (from Cloudflare)
    api_key = os.getenv("R2_API_KEY")
    if api_key:
        # Parse API key - format: "access_key_id:secret_access_key"
        if ":" in api_key:
            access_key, secret_key = api_key.split(":", 1)
        else:
            print("Error: R2_API_KEY must be in format 'access_key_id:secret_access_key'")
            sys.exit(1)
    else:
        # Fallback to separate keys (legacy)
        access_key = os.getenv("R2_ACCESS_KEY_ID")
        secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        print("Error: R2 credentials not found in environment variables")
        print("Required: R2_ACCOUNT_ID and R2_API_KEY")
        print("  OR: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
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

    print(f"Downloading bundles from R2: {bucket_name}/{prefix}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # List and download all bundle files
    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        bundle_count = 0
        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]

                # Skip directories
                if key.endswith("/"):
                    continue

                # Only download .bundle files
                if not key.endswith(".bundle"):
                    continue

                # Get filename and local path
                filename = Path(key).name
                local_path = output_dir / filename

                print(f"  Downloading: {filename} ({obj['Size'] / 1024 / 1024:.1f} MB)")

                s3.download_file(bucket_name, key, str(local_path))
                bundle_count += 1

        print(f"\n✅ Downloaded {bundle_count} bundles to {output_dir}")

    except Exception as e:
        print(f"❌ Error downloading bundles: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download FM bundles from R2")
    parser.add_argument(
        "--prefix",
        required=True,
        help="R2 prefix containing bundles (e.g., fm2025/StandaloneOSX)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory for downloaded bundles",
    )

    args = parser.parse_args()
    download_bundles(args.prefix, args.output)


if __name__ == "__main__":
    main()
