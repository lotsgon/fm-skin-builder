#!/usr/bin/env python3
"""
List bundles in R2 and split into groups for parallel processing.

This script queries R2 to get all bundle files under a prefix,
then splits them into N roughly equal groups for matrix processing.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config


def list_and_split_bundles(prefix: str, num_groups: int, output_dir: Path):
    """
    List bundles from R2 and split into groups.

    Args:
        prefix: R2 prefix containing bundles
        num_groups: Number of groups to split into
        output_dir: Directory to save group manifests
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

    # Initialize R2 client
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

    print(f"Listing bundles from R2: {bucket_name}/{prefix}")

    # List all bundle files
    bundle_keys = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                # Only include .bundle files
                if key.endswith(".bundle"):
                    bundle_keys.append(key)

        print(f"Found {len(bundle_keys)} bundle files")

    except Exception as e:
        print(f"Error listing bundles: {e}")
        sys.exit(1)

    if not bundle_keys:
        print("No bundle files found!")
        sys.exit(1)

    # Sort for deterministic splitting
    bundle_keys.sort()

    # Split into groups
    bundles_per_group = math.ceil(len(bundle_keys) / num_groups)
    groups = []

    for i in range(num_groups):
        start_idx = i * bundles_per_group
        end_idx = min((i + 1) * bundles_per_group, len(bundle_keys))

        if start_idx >= len(bundle_keys):
            break

        group_bundles = bundle_keys[start_idx:end_idx]
        groups.append({
            "group_id": i,
            "bundle_count": len(group_bundles),
            "bundles": group_bundles,
        })

        print(f"  Group {i}: {len(group_bundles)} bundles")

    # Save group manifests
    output_dir.mkdir(parents=True, exist_ok=True)

    for group in groups:
        group_file = output_dir / f"group_{group['group_id']}.json"
        with open(group_file, "w") as f:
            json.dump(group, f, indent=2)
        print(f"  Saved: {group_file}")

    # Save summary
    summary = {
        "total_bundles": len(bundle_keys),
        "num_groups": len(groups),
        "bundles_per_group": bundles_per_group,
        "groups": [
            {"group_id": g["group_id"], "bundle_count": g["bundle_count"]}
            for g in groups
        ],
    }

    summary_file = output_dir / "split_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n✅ Split into {len(groups)} groups")
    print(f"   Summary: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="List and split R2 bundles for parallel processing"
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="R2 prefix containing bundles (e.g., fm2025/StandaloneOSX)",
    )
    parser.add_argument(
        "--groups",
        type=int,
        default=10,
        help="Number of groups to split into (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("bundle_groups"),
        help="Output directory for group manifests (default: bundle_groups)",
    )

    args = parser.parse_args()
    list_and_split_bundles(args.prefix, args.groups, args.output)


if __name__ == "__main__":
    main()
