from __future__ import annotations

from pathlib import Path

import pytest

from take_home_router.service import ClassifierService

ROOT = Path(__file__).resolve().parents[1]


class NoExplorationRandom:
    """Keep shared service tests deterministic while production remains stochastic."""

    def random(self) -> float:
        return 0.999999

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        del start, stop, step
        return 0


@pytest.fixture(scope="session")
def service() -> ClassifierService:
    return ClassifierService.from_paths(
        s2_artifact_dir=ROOT / "artifacts" / "s2",
        auxiliary_artifact=ROOT / "artifacts" / "auxiliary" / "a2_matrixfact.json",
        config_path=ROOT / "config" / "router.json",
        random_source=NoExplorationRandom(),
    )
