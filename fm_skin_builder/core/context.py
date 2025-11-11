from __future__ import annotations

import gc
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional, Set

import UnityPy


@dataclass
class PatchReport:
    """Aggregates change information for a patched bundle."""

    bundle_path: Path
    assets_modified: Set[str] = field(default_factory=set)
    variables_patched: int = 0
    direct_patched: int = 0
    selector_conflicts: list[tuple[str, str, int]] = field(default_factory=list)
    dry_run: bool = False
    summary_lines: list[str] = field(default_factory=list)
    saved_path: Optional[Path] = None
    texture_replacements: int = 0
    font_replacements: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.assets_modified
            or self.variables_patched
            or self.direct_patched
            or self.texture_replacements
            or self.font_replacements
        )

    def mark_saved(self, path: Path) -> None:
        self.saved_path = path

    def extend_summary(self, lines: Iterable[str]) -> None:
        self.summary_lines.extend(lines)


class BundleContext:
    """Owns UnityPy environment lifecycle for a bundle path."""

    def __init__(
        self,
        bundle_path: Path,
        *,
        loader: Optional[Callable[[str], UnityPy.Environment]] = None,
        auto_backup: bool = False,
    ) -> None:
        self.bundle_path = bundle_path
        self._loader = loader or UnityPy.load
        self.auto_backup = auto_backup
        self._env: Optional[UnityPy.Environment] = None
        self._dirty = False

    def __enter__(self) -> "BundleContext":
        self.load()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.dispose()

    def load(self) -> None:
        if self._env is not None:
            return
        if self.auto_backup:
            self._ensure_backup()

        # Windows network path handling: fsspec has issues with network shares
        # (mapped drives, UNC paths, WebDAV, etc.)
        # Read the file with standard Python I/O first, then pass bytes to UnityPy
        bundle_path_str = str(self.bundle_path)
        is_network_path = False

        if os.name == "nt":
            # Detect network paths:
            # - UNC paths: \\server\share\...
            # - Mapped drives (common network letters): P: through Z:
            # - WebDAV paths containing localhost@
            if (
                bundle_path_str.startswith("\\\\")
                or bundle_path_str[0:1] in "PQRSTUVWXYZ"
                and bundle_path_str[1:2] == ":"
                or "localhost@" in bundle_path_str
            ):
                is_network_path = True

        if is_network_path:
            try:
                # For Windows network paths, read the file into memory and load from bytes
                # This bypasses fsspec's problematic network path handling
                with open(self.bundle_path, "rb") as f:
                    bundle_data = f.read()
                # UnityPy can load from bytes directly
                self._env = UnityPy.load(bundle_data)
                return
            except (OSError, IOError):
                # If reading fails, fall through to try the normal path
                pass

        # Normal path handling (local files, or if network read failed)
        bundle_str = str(self.bundle_path)
        if os.name == "nt":
            # On Windows, normalize path separators to forward slashes for fsspec
            bundle_str = bundle_str.replace("\\", "/")

        self._env = self._loader(bundle_str)

    @property
    def env(self) -> UnityPy.Environment:
        if self._env is None:
            self.load()
        return self._env  # type: ignore[return-value]

    def mark_dirty(self) -> None:
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def save_modified(
        self,
        out_dir: Path,
        *,
        dry_run: bool = False,
        suffix: str = "",
    ) -> Optional[Path]:
        if not self._dirty or dry_run:
            return None
        self.load()
        out_dir.mkdir(parents=True, exist_ok=True)
        name, ext = os.path.splitext(self.bundle_path.name)
        out_path = out_dir / f"{name}{suffix}{ext}"
        with out_path.open("wb") as fh:
            fh.write(self.env.file.save())
        self._cleanup_stray_originals(out_dir, name, ext, out_path)
        return out_path

    def dispose(self) -> None:
        if self._env is not None:
            try:
                del self._env
            except Exception:
                self._env = None
                gc.collect()
                raise
            else:
                self._env = None
                gc.collect()

    def _ensure_backup(self) -> None:
        backup = self.bundle_path.with_suffix(self.bundle_path.suffix + ".bak")
        if backup.exists():
            return
        try:
            shutil.copy2(self.bundle_path, backup)
        except Exception:
            # Backup best-effort only.
            return

    def _cleanup_stray_originals(
        self, out_dir: Path, name: str, ext: str, new_path: Path
    ) -> None:
        orig_out_file = out_dir / f"{name}{ext}"
        if orig_out_file.exists() and orig_out_file != new_path:
            try:
                orig_out_file.unlink()
            except Exception:
                # Best-effort cleanup; ignore errors if file cannot be deleted.
                pass
        cwd_orig_file = Path.cwd() / f"{name}{ext}"
        if cwd_orig_file.exists() and cwd_orig_file not in {new_path, orig_out_file}:
            try:
                cwd_orig_file.unlink()
            except Exception:
                # Best-effort cleanup; ignore errors if file cannot be deleted.
                pass
