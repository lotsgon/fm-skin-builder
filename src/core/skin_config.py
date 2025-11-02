"""Parses and validates skin config.json."""
import json
from pathlib import Path
from typing import Any

class SkinConfig:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {}

    def load(self) -> None:
        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    @property
    def overrides(self) -> dict[str, str]:
        return self.data.get("overrides", {})
