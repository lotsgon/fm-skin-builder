from __future__ import annotations
import argparse
from .commands import (
    build as cmd_build,
    extract as cmd_extract,
    verify as cmd_verify,
    swap as cmd_swap,
    patch as cmd_patch,
    scan as cmd_scan,
    catalogue as cmd_catalogue,
)
import os
import sys
import gc


def entrypoint():
    main()


def main() -> None:
    parser = argparse.ArgumentParser(description="Football Manager Skin Builder CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Build a skin from folder")
    b.add_argument("skin_dir", type=str)
    b.add_argument("--out", type=str, default="build")

    sub.add_parser("extract", help="Extract assets (stub)")
    sub.add_parser("verify", help="Verify loads (stub)")
    sub.add_parser("swap", help="Swap bundles (stub)")

    p = sub.add_parser("patch", help="Patch bundles using CSS/USS overrides")
    p.add_argument(
        "css", type=str, help="Skin folder or directory containing .css/.uss overrides"
    )
    p.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory for modified bundles (defaults to <skin>/packages)",
    )
    p.add_argument(
        "--bundle",
        type=str,
        default=None,
        help="Optional bundle file or directory (if omitted, inferred from skin config)",
    )
    p.add_argument(
        "--patch-direct", action="store_true", help="Also patch inlined color literals"
    )
    p.add_argument(
        "--debug-export",
        action="store_true",
        help="Export .uss and JSON (original/patched) for debugging",
    )
    p.add_argument(
        "--backup",
        action="store_true",
        help="Backup original bundle(s) before patching",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and report changes without writing any files",
    )
    p.add_argument(
        "--no-scan-cache",
        action="store_true",
        help="Do not use cached scan indices even if available",
    )
    p.add_argument(
        "--refresh-scan-cache",
        action="store_true",
        help="Force refresh of scan cache before patching (if a skin config is present)",
    )

    s = sub.add_parser("scan", help="Scan bundles and index stylesheet usage")
    s.add_argument(
        "--bundle", type=str, required=True, help="Bundle file or directory to scan"
    )
    s.add_argument(
        "--out",
        type=str,
        default="build/scan",
        help="Output directory for scan index and USS exports",
    )
    s.add_argument(
        "--export-uss",
        action="store_true",
        help="Export all stylesheet assets as .uss alongside the index",
    )

    c = sub.add_parser(
        "catalogue", help="Build comprehensive asset catalogue from FM bundles"
    )
    c.add_argument(
        "--bundle", type=str, required=True, help="Bundle file or directory to scan"
    )
    c.add_argument(
        "--out",
        type=str,
        default="build/catalogue",
        help="Output directory for catalogue",
    )
    c.add_argument(
        "--fm-version",
        type=str,
        required=True,
        help="FM version string (e.g., '2026.4.0')",
    )
    c.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    c.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )

    # Catalogue diff command
    d = sub.add_parser(
        "catalogue-diff", help="Compare two catalogue versions and generate changelog"
    )
    d.add_argument(
        "--old",
        type=str,
        required=True,
        help="Path to old catalogue version directory",
    )
    d.add_argument(
        "--new",
        type=str,
        required=True,
        help="Path to new catalogue version directory",
    )
    d.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory for changelog (defaults to new version directory)",
    )
    d.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    # Catalogue note command
    n = sub.add_parser(
        "catalogue-note", help="Add or view notes for a catalogue version"
    )
    n.add_argument(
        "--catalogue-dir",
        type=str,
        required=True,
        help="Path to catalogue version directory",
    )
    n.add_argument(
        "--note",
        type=str,
        default=None,
        help="Note to add (if omitted, displays current notes)",
    )
    n.add_argument(
        "--append",
        action="store_true",
        help="Append to existing notes instead of replacing",
    )

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
    elif args.command == "catalogue":
        cmd_catalogue.run(args)
    elif args.command == "catalogue-diff":
        from .commands import catalogue_diff as cmd_catalogue_diff
        cmd_catalogue_diff.run(args)
    elif args.command == "catalogue-note":
        from .commands import catalogue_note as cmd_catalogue_note
        cmd_catalogue_note.run(args)

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
