#!/usr/bin/env python3
"""
Download bundles for a specific group from R2.

This script reads a group manifest (created by split_bundles.py) and downloads
only the bundles specified in that group for parallel processing.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config


def download_bundle_group(group_file: Path, output_dir: Path):
    """
    Download bundles specified in a group manifest.

    Args:
        group_file: Path to group manifest JSON file
        output_dir: Directory to save downloaded bundles
    """
    # Get R2 credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("R2_BUNDLES_BUCKET", "fm-skin-builder-bundles")

    if not all([account_id, access_key, secret_key]):
        print("Error: R2 credentials not found in environment variables")
        print("Required: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
        sys.exit(1)

    # Read group manifest
    if not group_file.exists():
        print(f"Error: Group manifest not found: {group_file}")
        sys.exit(1)

    with open(group_file) as f:
        group_data = json.load(f)

    group_id = group_data["group_id"]
    bundles = group_data["bundles"]

    print(f"📦 Downloading Group {group_id}")
    print(f"   Bundles: {len(bundles)}")
    print(f"   Bucket: {bucket_name}")

    # Initialize R2 client
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download each bundle
    success_count = 0
    for i, bundle_key in enumerate(bundles, 1):
        # Preserve the directory structure
        local_path = output_dir / bundle_key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            print(f"  [{i}/{len(bundles)}] Downloading {bundle_key}")
            s3.download_file(bucket_name, bundle_key, str(local_path))
            success_count += 1
        except Exception as e:
            print(f"  ❌ Error downloading {bundle_key}: {e}")
            # Continue with other bundles rather than failing completely
            continue

    print(f"\n✅ Downloaded {success_count}/{len(bundles)} bundles")

    if success_count == 0:
        print("Error: No bundles were downloaded successfully")
        sys.exit(1)

    return success_count


def main():
    parser = argparse.ArgumentParser(
        description="Download bundles for a specific group from R2"
    )
    parser.add_argument(
        "--group-file",
        type=Path,
        required=True,
        help="Path to group manifest JSON file (e.g., bundle_groups/group_0.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("bundles"),
        help="Output directory for downloaded bundles (default: bundles)",
    )

    args = parser.parse_args()
    download_bundle_group(args.group_file, args.output)


if __name__ == "__main__":
    main()
