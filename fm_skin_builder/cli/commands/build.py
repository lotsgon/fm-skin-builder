from __future__ import annotations
from pathlib import Path
from ...core.patcher import apply_overrides

def run(args) -> None:
    apply_overrides(Path(args.skin_dir), Path(args.out))
