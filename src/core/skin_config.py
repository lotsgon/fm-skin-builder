from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from pathlib import Path
import json


class SkinConfigModel(BaseModel):
    # New schema v2: metadata + includes only
    schema_version: int = Field(2, ge=2)
    name: str
    author: Optional[str] = None
    version: Optional[str] = None
    includes: Optional[List[str]] = None
    description: Optional[str] = None

    # Optional UXML overrides: {asset_name: file_path}
    uxml_overrides: Optional[Dict[str, str]] = None


class SkinConfig:
    def __init__(self, path: Path):
        self.path = path
        self.model: Optional[SkinConfigModel] = None

    def load(self) -> SkinConfigModel:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.model = SkinConfigModel.model_validate(data)
        return self.model
