from __future__ import annotations
import argparse
from .commands import build as cmd_build, extract as cmd_extract, verify as cmd_verify, swap as cmd_swap

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

    args = parser.parse_args()

    if args.command == "build":
        cmd_build.run(args)
    elif args.command == "extract":
        cmd_extract.run(args)
    elif args.command == "verify":
        cmd_verify.run(args)
    elif args.command == "swap":
        cmd_swap.run(args)

if __name__ == "__main__":
    main()
