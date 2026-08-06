from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

import pytest

from take_home_router.policy import select_model


@dataclass(frozen=True)
class Prediction:
    candidate: str
    quality: float
    expected_output_tokens: int = 100
    uncertainty: float = 0.1


@dataclass
class ScriptedRandom:
    roll: float
    index: int
    index_calls: int = 0

    def random(self) -> float:
        return self.roll

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        assert stop is None
        assert step == 1
        assert start > 0
        self.index_calls += 1
        return self.index


def predictions() -> dict[str, Prediction]:
    return {
        "cheap": Prediction("cheap", 0.80),
        "strong": Prediction("strong", 0.90),
    }


def test_policy_preference_endpoints_and_benchmark_midpoint() -> None:
    costs = {"cheap": 0.01, "strong": 0.10}

    quality_only = select_model(predictions(), costs, lambda_penalty=3.0, cost_saving_preference=0)
    midpoint = select_model(predictions(), costs, lambda_penalty=3.0, cost_saving_preference=50)
    cost_only = select_model(predictions(), costs, lambda_penalty=3.0, cost_saving_preference=100)

    assert quality_only.selected_model == "strong"
    assert midpoint.selected_model == "cheap"
    assert cost_only.selected_model == "cheap"
    assert midpoint.candidates[0].quality_component == pytest.approx(0.4)  # pyright: ignore
    assert midpoint.candidates[0].cost_penalty == pytest.approx(0.015)  # pyright: ignore


def test_equal_utility_prefers_lower_cost_then_stable_model_id() -> None:
    equal = {
        "z": Prediction("z", 0.8),
        "a": Prediction("a", 0.8),
    }
    lower_cost = select_model(
        equal,
        {"z": 0.1, "a": 0.01},
        lambda_penalty=0,
        cost_saving_preference=0,
    )
    same_cost = select_model(
        equal,
        {"z": 0.01, "a": 0.01},
        lambda_penalty=0,
        cost_saving_preference=0,
    )

    assert lower_cost.selected_model == "a"
    assert same_cost.selected_model == "a"


def test_random_exploration_can_override_the_scored_winner() -> None:
    source = ScriptedRandom(roll=0.29, index=1)

    result = select_model(
        predictions(),
        {"cheap": 0.01, "strong": 0.10},
        lambda_penalty=3,
        cost_saving_preference=0,
        random_selection_probability=0.3,
        random_source=source,
    )

    assert result.selection_mode == "random"
    assert result.random_selection_probability == 0.3
    assert result.selected_model == "cheap"
    assert result.candidates[0].model == "cheap"
    assert source.index_calls == 1


def test_exploration_boundary_keeps_the_scored_winner() -> None:
    source = ScriptedRandom(roll=0.3, index=1)

    result = select_model(
        predictions(),
        {"cheap": 0.01, "strong": 0.10},
        lambda_penalty=3,
        cost_saving_preference=0,
        random_selection_probability=0.3,
        random_source=source,
    )

    assert result.selection_mode == "scored"
    assert result.selected_model == "strong"
    assert source.index_calls == 0


def test_seeded_exploration_is_near_30_percent_and_uniform() -> None:
    source = random.Random(23)
    random_models: Counter[str] = Counter()
    total = 10_000
    for _ in range(total):
        result = select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=50,
            random_selection_probability=0.3,
            random_source=source,
        )
        if result.selection_mode == "random":
            random_models[result.selected_model] += 1

    random_total = sum(random_models.values())
    assert 0.28 <= random_total / total <= 0.32
    assert set(random_models) == {"cheap", "strong"}
    assert 0.47 <= random_models["cheap"] / random_total <= 0.53


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_invalid_preferences_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=value,
        )


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_random_selection_probabilities_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=50,
            random_selection_probability=value,
            random_source=ScriptedRandom(roll=0, index=0),
        )


def test_random_source_is_required_when_exploration_is_enabled() -> None:
    with pytest.raises(ValueError, match="random_source is required"):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=50,
            random_selection_probability=0.3,
        )


@pytest.mark.parametrize("roll", [-0.1, 1.0, float("nan"), float("inf")])
def test_invalid_random_source_draws_fail_closed(roll: float) -> None:
    with pytest.raises(ValueError, match=r"outside \[0, 1\)"):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=50,
            random_selection_probability=0.3,
            random_source=ScriptedRandom(roll=roll, index=0),
        )


@pytest.mark.parametrize("index", [-1, 2])
def test_invalid_random_candidate_indices_fail_closed(index: int) -> None:
    with pytest.raises(ValueError, match="out-of-range candidate index"):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=50,
            random_selection_probability=0.3,
            random_source=ScriptedRandom(roll=0.0, index=index),
        )
