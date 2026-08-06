from __future__ import annotations

import json
from pathlib import Path

import pytest

from take_home_router.config import ConfigurationError, RouterConfig

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "router.json"


def test_runtime_config_enables_30_percent_random_selection() -> None:
    config = RouterConfig.load(CONFIG_PATH)

    assert config.schema_version == 2
    assert config.classifier_version.endswith("-random-30")
    assert config.random_selection_probability == 0.3


@pytest.mark.parametrize("value", [None, "0.3", -0.1, 1.1])
def test_runtime_config_rejects_invalid_random_selection_probability(
    tmp_path: Path,
    value: object,
) -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["random_selection_probability"] = value
    path = tmp_path / "router.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="random_selection_probability"):
        RouterConfig.load(path)
