#!/usr/bin/env python3
"""
List bundles in R2 and split into groups for parallel processing.

This script queries R2 to get all bundle files under a prefix,
then splits them into N roughly equal groups for matrix processing.

Features:
- Exclude specific bundles (e.g., newgen faces)
- Keep scale variants together (_1x, _2x, _3x, _4x)
- Balance bundle distribution across groups
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Set

import boto3
from botocore.client import Config


def get_bundle_base_name(bundle_path: str) -> str:
    """
    Extract base name from bundle path, removing scale suffixes.

    Examples:
        ui-iconspriteatlases_assets_1x.bundle -> ui-iconspriteatlases_assets
        ui-iconspriteatlases_assets_2x.bundle -> ui-iconspriteatlases_assets
        skins.bundle -> skins
    """
    # Get filename without path
    filename = bundle_path.split('/')[-1]
    # Remove .bundle extension
    name = filename.replace('.bundle', '')
    # Remove scale suffixes: _1x, _2x, _3x, _4x, @1x, @2x, etc.
    base = re.sub(r'[_@]\d+x$', '', name)
    return base


def group_related_bundles(bundle_keys: List[str], exclude_patterns: List[str]) -> List[List[str]]:
    """
    Group related bundles together (e.g., scale variants).
    Excludes bundles matching exclude patterns.

    Returns:
        List of bundle groups, where each group contains related bundles
    """
    # Filter out excluded bundles
    filtered_bundles = []
    excluded_count = 0

    for bundle_key in bundle_keys:
        excluded = False
        for pattern in exclude_patterns:
            if pattern.lower() in bundle_key.lower():
                print(f"  ⏭️  Excluding: {bundle_key}")
                excluded = True
                excluded_count += 1
                break
        if not excluded:
            filtered_bundles.append(bundle_key)

    if excluded_count > 0:
        print(f"  Excluded {excluded_count} bundles")

    # Group by base name
    groups_dict: Dict[str, List[str]] = {}

    for bundle_key in filtered_bundles:
        base_name = get_bundle_base_name(bundle_key)
        if base_name not in groups_dict:
            groups_dict[base_name] = []
        groups_dict[base_name].append(bundle_key)

    # Convert to list of groups, sorted for determinism
    bundle_groups = [
        sorted(bundles)
        for bundles in sorted(groups_dict.values(), key=lambda x: x[0])
    ]

    return bundle_groups


def distribute_to_groups(bundle_groups: List[List[str]], num_groups: int) -> List[List[str]]:
    """
    Distribute bundle groups across N groups, trying to balance the load.

    Uses a greedy bin-packing approach: assign each bundle group to the
    group with the fewest bundles so far.
    """
    # Initialize empty groups
    groups = [[] for _ in range(num_groups)]
    group_sizes = [0] * num_groups

    # Sort bundle groups by size (largest first) for better packing
    sorted_bundle_groups = sorted(bundle_groups, key=len, reverse=True)

    # Assign each bundle group to the group with fewest bundles
    for bundle_group in sorted_bundle_groups:
        # Find group with minimum size
        min_idx = group_sizes.index(min(group_sizes))

        # Add all bundles from this group
        groups[min_idx].extend(bundle_group)
        group_sizes[min_idx] += len(bundle_group)

    return groups


def list_and_split_bundles(
    prefix: str,
    num_groups: int,
    output_dir: Path,
    exclude_patterns: List[str]
):
    """
    List bundles from R2 and split into groups.

    Args:
        prefix: R2 prefix containing bundles
        num_groups: Number of groups to split into
        output_dir: Directory to save group manifests
        exclude_patterns: List of patterns to exclude from processing
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

    print(f"📦 Listing bundles from R2: {bucket_name}/{prefix}")
    if exclude_patterns:
        print(f"🚫 Exclude patterns: {', '.join(exclude_patterns)}")

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

        print(f"✅ Found {len(bundle_keys)} bundle files")

    except Exception as e:
        print(f"❌ Error listing bundles: {e}")
        sys.exit(1)

    if not bundle_keys:
        print("❌ No bundle files found!")
        sys.exit(1)

    # Group related bundles and exclude unwanted ones
    print(f"\n📋 Grouping related bundles...")
    bundle_groups = group_related_bundles(bundle_keys, exclude_patterns)
    print(f"✅ Created {len(bundle_groups)} bundle groups")

    # Show some examples of grouped bundles
    print(f"\n📊 Example grouped bundles:")
    for i, group in enumerate(bundle_groups[:5]):
        if len(group) > 1:
            base = get_bundle_base_name(group[0])
            scales = [b.split('/')[-1] for b in group]
            print(f"  {base}: {', '.join(scales)}")
    if len(bundle_groups) > 5:
        print(f"  ... and {len(bundle_groups) - 5} more groups")

    # Distribute to processing groups
    print(f"\n🔀 Distributing to {num_groups} processing groups...")
    groups = distribute_to_groups(bundle_groups, num_groups)

    # Filter out empty groups
    groups = [g for g in groups if len(g) > 0]

    # Save group manifests
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, group_bundles in enumerate(groups):
        group_data = {
            "group_id": i,
            "bundle_count": len(group_bundles),
            "bundles": group_bundles,
        }

        group_file = output_dir / f"group_{i}.json"
        with open(group_file, "w") as f:
            json.dump(group_data, f, indent=2)

        print(f"  Group {i}: {len(group_bundles)} bundles → {group_file.name}")

    # Save summary
    total_bundles = sum(len(g) for g in groups)
    summary = {
        "total_bundles": total_bundles,
        "num_groups": len(groups),
        "excluded_patterns": exclude_patterns,
        "groups": [
            {"group_id": i, "bundle_count": len(g)}
            for i, g in enumerate(groups)
        ],
    }

    summary_file = output_dir / "split_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Split {total_bundles} bundles into {len(groups)} groups")
    print(f"   Summary: {summary_file}")

    # Show distribution stats
    bundle_counts = [len(g) for g in groups]
    print(f"\n📊 Distribution:")
    print(f"   Min: {min(bundle_counts)} bundles")
    print(f"   Max: {max(bundle_counts)} bundles")
    print(f"   Avg: {sum(bundle_counts) / len(bundle_counts):.1f} bundles")


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
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["newgen", "regen"],
        help="Bundle name patterns to exclude (default: newgen, regen)",
    )

    args = parser.parse_args()
    list_and_split_bundles(
        args.prefix,
        args.groups,
        args.output,
        args.exclude
    )


if __name__ == "__main__":
    main()
