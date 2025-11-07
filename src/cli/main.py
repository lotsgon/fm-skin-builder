from __future__ import annotations
import argparse
from .commands import build as cmd_build, extract as cmd_extract, verify as cmd_verify, swap as cmd_swap, patch as cmd_patch, scan as cmd_scan
import os
import sys
import gc


def entrypoint():
    main()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Football Manager Skin Builder CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Build a skin from folder")
    b.add_argument("skin_dir", type=str)
    b.add_argument("--out", type=str, default="build")

    sub.add_parser("extract", help="Extract assets (stub)")
    sub.add_parser("verify", help="Verify loads (stub)")
    sub.add_parser("swap", help="Swap bundles (stub)")

    p = sub.add_parser("patch", help="Patch bundles using CSS/USS overrides")
    p.add_argument(
        "css", type=str, help="Skin folder or directory containing .css/.uss overrides")
    p.add_argument("--out", type=str, default=None,
                   help="Output directory for modified bundles (defaults to <skin>/packages)")
    p.add_argument("--bundle", type=str, default=None,
                   help="Optional bundle file or directory (if omitted, inferred from skin config)")
    p.add_argument("--patch-direct", action="store_true",
                   help="Also patch inlined color literals")
    p.add_argument("--debug-export", action="store_true",
                   help="Export .uss and JSON (original/patched) for debugging")
    p.add_argument("--backup", action="store_true",
                   help="Backup original bundle(s) before patching")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute and report changes without writing any files")
    p.add_argument("--no-scan-cache", action="store_true",
                   help="Do not use cached scan indices even if available")
    p.add_argument("--refresh-scan-cache", action="store_true",
                   help="Force refresh of scan cache before patching (if a skin config is present)")

    s = sub.add_parser("scan", help="Scan bundles and index stylesheet usage")
    s.add_argument("--bundle", type=str, required=True,
                   help="Bundle file or directory to scan")
    s.add_argument("--out", type=str, default="build/scan",
                   help="Output directory for scan index and USS exports")
    s.add_argument("--export-uss", action="store_true",
                   help="Export all stylesheet assets as .uss alongside the index")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build.run(args)
    elif args.command == "extract":
        cmd_extract.run(args)
    elif args.command == "verify":
        cmd_verify.run(args)
    elif args.command == "swap":
        cmd_swap.run(args)
    elif args.command == "patch":
        cmd_patch.run(args)
    elif args.command == "scan":
        cmd_scan.run(args)

    # Mitigate rare CPython finalization crash observed with C extensions (e.g., compression libs)
    # by forcing an immediate process exit after flushing. Can be disabled by setting FM_HARD_EXIT=0.
    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.flush()
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass
    if os.environ.get("FM_HARD_EXIT", "1") not in {"0", "false", "False"}:
        os._exit(0)


if __name__ == "__main__":
    main()
