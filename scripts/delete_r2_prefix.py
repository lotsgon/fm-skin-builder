#!/usr/bin/env python3
"""
Delete objects from R2 bucket with a specific prefix.

Usage:
    python scripts/delete_r2_prefix.py --prefix "fm2025/StandaloneOSX"
    python scripts/delete_r2_prefix.py --prefix "fm2025/StandaloneOSX" --dry-run
"""

import argparse
import os
import sys

import boto3
from botocore.client import Config


def delete_r2_prefix(bucket_name: str, prefix: str, dry_run: bool = False):
    """
    Delete all objects in R2 bucket that start with the given prefix.

    Args:
        bucket_name: R2 bucket name
        prefix: Prefix to match for deletion (e.g., "fm2025/StandaloneOSX")
        dry_run: If True, only list objects without deleting them
    """
    # Get R2 credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([account_id, access_key, secret_key]):
        print("Error: R2 credentials not found in environment variables")
        print("\nRequired:")
        print('  export R2_ACCOUNT_ID="your-account-id"')
        print('  export R2_ACCESS_KEY_ID="your-access-key-id"')
        print('  export R2_SECRET_ACCESS_KEY="your-secret-access-key"')
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

    print(f"Deleting objects from R2: {bucket_name}")
    print(f"  Prefix: {prefix}")
    if dry_run:
        print("  DRY RUN MODE - No objects will be deleted")
    print()
    objects_to_delete = []
    continuation_token = None

    while True:
        list_kwargs = {
            "Bucket": bucket_name,
            "Prefix": prefix,
        }
        if continuation_token:
            list_kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**list_kwargs)

        if "Contents" in response:
            for obj in response["Contents"]:
                objects_to_delete.append({"Key": obj["Key"]})
                print(f"  Found: {obj['Key']} ({obj['Size']} bytes)")

        if response.get("IsTruncated"):
            continuation_token = response.get("NextContinuationToken")
        else:
            break

    if not objects_to_delete:
        print(f"  No objects found with prefix: {prefix}")
        return

    print(f"\nFound {len(objects_to_delete)} objects to delete")

    if dry_run:
        print("  Dry run - skipping deletion")
        return

    print(f"\nDeleting {len(objects_to_delete)} objects...")

    # Delete objects in batches (AWS S3 limit is 1000 per request)
    batch_size = 1000
    deleted_count = 0

    for i in range(0, len(objects_to_delete), batch_size):
        batch = objects_to_delete[i : i + batch_size]

        try:
            delete_response = s3.delete_objects(
                Bucket=bucket_name,
                Delete={
                    "Objects": batch,
                    "Quiet": True,  # Don't return deleted object info
                },
            )

            if "Errors" in delete_response:
                for error in delete_response["Errors"]:
                    print(f"  ❌ Error deleting {error['Key']}: {error['Message']}")

            if "Deleted" in delete_response:
                deleted_count += len(delete_response["Deleted"])
                print(
                    f"  ✅ Deleted batch of {len(delete_response['Deleted'])} objects"
                )

        except Exception as e:
            print(f"  ❌ Error deleting batch: {e}")
            continue

    print(f"\n✅ Successfully deleted {deleted_count} objects with prefix: {prefix}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete objects from R2 bucket with a specific prefix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/delete_r2_prefix.py --prefix "fm2025/StandaloneOSX"
  python scripts/delete_r2_prefix.py --prefix "fm2025/StandaloneOSX" --dry-run
  python scripts/delete_r2_prefix.py --prefix "old-data/" --bucket "my-bucket"

Environment variables required:
  R2_ACCOUNT_ID        - Your Cloudflare R2 account ID
  R2_ACCESS_KEY_ID     - R2 Access Key ID from API token
  R2_SECRET_ACCESS_KEY - R2 Secret Access Key from API token

Optional environment variables:
  R2_BUCKET            - R2 bucket name (default: fm-skin-builder-bundles)
        """,
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Prefix to match for deletion (e.g., fm2025/StandaloneOSX)",
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("R2_BUCKET", "fm-skin-builder-bundles"),
        help="R2 bucket name (default: fm-skin-builder-bundles)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List objects that would be deleted without actually deleting them",
    )

    args = parser.parse_args()
    delete_r2_prefix(args.bucket, args.prefix, args.dry_run)


if __name__ == "__main__":
    main()
