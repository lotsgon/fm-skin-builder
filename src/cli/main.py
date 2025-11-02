"""CLI entrypoint."""
import argparse
from pathlib import Path
from ..core.patcher import apply_overrides

def main() -> None:
    parser = argparse.ArgumentParser(description="Football Manager Skin Builder CLI")
    sub = parser.add_subparsers(dest="command")

    build = sub.add_parser("build", help="Build a skin from folder")
    build.add_argument("skin_dir", type=Path)
    build.add_argument("--out", type=Path, default=Path("./build"))

    args = parser.parse_args()
    if args.command == "build":
        apply_overrides(args.skin_dir, args.out)

if __name__ == "__main__":
    main()
