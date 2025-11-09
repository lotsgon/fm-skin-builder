from __future__ import annotations
from pathlib import Path
from ...core.bundle_inspector import scan_target


def run(args) -> None:
    bundle = Path(args.bundle)
    out_dir = Path(args.out)
    scan_target(bundle=bundle, out_dir=out_dir, export_uss=args.export_uss)
