from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict
from pathlib import Path
import json


class SkinConfigModel(BaseModel):
    schema_version: int = Field(1, ge=1)
    name: str
    target_bundle: str
    output_bundle: str
    overrides: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = None


class SkinConfig:
    def __init__(self, path: Path):
        self.path = path
        self.model: Optional[SkinConfigModel] = None

    def load(self) -> SkinConfigModel:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.model = SkinConfigModel.model_validate(data)
        return self.model
