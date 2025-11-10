#!/usr/bin/env python3
"""
Upload FM bundles from local machine to R2 for cloud processing.

Usage:
    python scripts/upload_bundles_to_r2.py \
        --bundles "~/Library/Application Support/Steam/.../StandaloneOSX" \
        --prefix "fm2025/StandaloneOSX"
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config


def upload_bundles(bundles_dir: Path, prefix: str):
    """
    Upload bundle files to R2.

    Args:
        bundles_dir: Local directory containing .bundle files
        prefix: R2 prefix/folder to upload to
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
        print("\nRequired: R2_ACCOUNT_ID and R2_API_KEY")
        print('  export R2_ACCOUNT_ID="your-account-id"')
        print('  export R2_API_KEY="access_key:secret_key"')
        print("\nOR (legacy):")
        print('  export R2_ACCESS_KEY_ID="your-access-key"')
        print('  export R2_SECRET_ACCESS_KEY="your-secret-key"')
        sys.exit(1)

    # Expand ~ and convert to absolute path
    bundles_dir = Path(bundles_dir).expanduser().resolve()

    if not bundles_dir.exists():
        print(f"Error: Bundles directory not found: {bundles_dir}")
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

    print(f"Uploading bundles to R2: {bucket_name}/{prefix}")
    print(f"  Source: {bundles_dir}")

    # Find all .bundle files
    bundle_files = list(bundles_dir.glob("*.bundle"))

    if not bundle_files:
        print(f"  No .bundle files found in {bundles_dir}")
        sys.exit(1)

    print(f"  Found {len(bundle_files)} bundle files")

    # Upload each bundle
    uploaded_count = 0
    total_size = 0

    for bundle_file in bundle_files:
        # R2 key: prefix + filename
        r2_key = f"{prefix}/{bundle_file.name}"

        file_size = bundle_file.stat().st_size
        print(f"  Uploading: {bundle_file.name} ({file_size / 1024 / 1024:.1f} MB)... ", end="")
        sys.stdout.flush()

        try:
            s3.upload_file(
                str(bundle_file),
                bucket_name,
                r2_key,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            print("✅")
            uploaded_count += 1
            total_size += file_size
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    print(f"\n✅ Uploaded {uploaded_count}/{len(bundle_files)} bundles ({total_size / 1024 / 1024:.1f} MB)")
    print(f"   R2 Location: {bucket_name}/{prefix}/")


def main():
    parser = argparse.ArgumentParser(
        description="Upload FM bundles to R2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python scripts/upload_bundles_to_r2.py \\
    --bundles "~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX" \\
    --prefix "fm2025/StandaloneOSX"

Environment variables required:
  R2_ACCOUNT_ID     - Your Cloudflare R2 account ID
  R2_API_KEY        - R2 API key in format "access_key_id:secret_access_key"
  R2_BUNDLES_BUCKET - R2 bucket name (default: fm-bundles)
        """,
    )
    parser.add_argument(
        "--bundles",
        required=True,
        type=Path,
        help="Directory containing FM bundle files",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="R2 prefix to upload to (e.g., fm2025/StandaloneOSX)",
    )

    args = parser.parse_args()
    upload_bundles(args.bundles, args.prefix)


if __name__ == "__main__":
    main()
