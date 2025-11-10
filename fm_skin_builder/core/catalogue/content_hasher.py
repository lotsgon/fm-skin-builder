"""
Content Hasher

SHA256 hashing for asset deduplication and integrity verification.
"""

from __future__ import annotations
import hashlib
from typing import Union


def compute_hash(data: Union[bytes, str]) -> str:
    """
    Compute SHA256 hash of data.

    Args:
        data: Bytes or string to hash

    Returns:
        Hex string of SHA256 hash
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashlib.sha256(data).hexdigest()


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA256 hash
    """
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)

    return hasher.hexdigest()
