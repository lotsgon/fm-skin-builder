from pathlib import Path
from src.core.cache import load_or_cache_config

def test_config_cache(tmp_path: Path):
    skin = tmp_path / "skin"
    (skin / "colours").mkdir(parents=True)
    cfg = skin / "config.json"
    cfg.write_text('{"schema_version":1,"name":"Test","target_bundle":"fm_base.bundle","output_bundle":"fm_base.bundle","overrides":{}}', encoding="utf-8")
    model = load_or_cache_config(skin)
    assert model.name == "Test"
