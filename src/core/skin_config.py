from __future__ import annotations
from pydantic import BaseModel, Field
from pathlib import Path
import json

class SkinConfigModel(BaseModel):
    schema_version: int = Field(1, ge=1)
    name: str
    target_bundle: str
    output_bundle: str
    overrides: dict[str, str] = Field(default_factory=dict)
    description: str | None = None

class SkinConfig:
    def __init__(self, path: Path):
        self.path = path
        self.model: SkinConfigModel | None = None

    def load(self) -> SkinConfigModel:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.model = SkinConfigModel.model_validate(data)
        return self.model
