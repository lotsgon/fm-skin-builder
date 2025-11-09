from pathlib import Path
from fm_skin_builder.core.cache import load_or_cache_config


def test_config_cache(tmp_path: Path):
    skin = tmp_path / "skin"
    (skin / "colours").mkdir(parents=True)
    cfg = skin / "config.json"
    cfg.write_text(
        '{"schema_version":2,"name":"Test","includes":["colours"]}', encoding="utf-8")
    model = load_or_cache_config(skin)
    assert model.name == "Test"
