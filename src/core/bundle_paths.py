from __future__ import annotations

import os
from pathlib import Path
from typing import List

from .logger import get_logger

log = get_logger(__name__)


def infer_bundle_files(css_dir: Path) -> List[Path]:
    """Infer bundle file(s) from Football Manager 26 default install locations."""

    try:
        import platform as _plat

        sysname = _plat.system()
    except Exception:
        sysname = ""

    candidates: List[Path] = []
    if sysname == "Windows":
        candidates.extend(
            [
                Path(
                    r"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Football Manager 26\\fm_Data\\StreamingAssets\\aa\\StandaloneWindows64"
                ),
                Path(
                    r"C:\\Program Files\\Epic Games\\Football Manager 26\\fm_Data\\StreamingAssets\\aa\\StandaloneWindows64"
                ),
            ]
        )
    elif sysname == "Darwin":
        candidates.extend(
            [
                Path(
                    os.path.expanduser(
                        "~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX"
                    )
                ),
                Path(
                    os.path.expanduser(
                        "~/Library/Application Support/Steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal"
                    )
                ),
                Path(
                    os.path.expanduser(
                        "~/Library/Application Support/Epic/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal"
                    )
                ),
            ]
        )
    elif sysname == "Linux":
        candidates.extend(
            [
                Path(
                    os.path.expanduser(
                        "~/.local/share/Steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneLinux64"
                    )
                ),
                Path(
                    os.path.expanduser(
                        "~/.steam/steam/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneLinux64"
                    )
                ),
            ]
        )

    for base in candidates:
        if base.exists() and base.is_dir():
            bundles = sorted(
                [p for p in base.iterdir() if p.suffix == ".bundle"])
            if bundles:
                log.info("Inferred bundles directory from FM install: %s", base)
                return bundles

    return []
