from __future__ import annotations

from pathlib import Path

import pytest

from take_home_router.service import ClassifierService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def service() -> ClassifierService:
    return ClassifierService.from_paths(
        s2_artifact_dir=ROOT / "artifacts" / "s2",
        auxiliary_artifact=ROOT / "artifacts" / "auxiliary" / "a2_matrixfact.json",
        config_path=ROOT / "config" / "router.json",
    )
