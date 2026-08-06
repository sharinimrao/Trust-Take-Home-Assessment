from __future__ import annotations

from dataclasses import dataclass

import pytest

from take_home_router.policy import select_model


@dataclass(frozen=True)
class Prediction:
    candidate: str
    quality: float
    expected_output_tokens: int = 100
    uncertainty: float = 0.1


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


@pytest.mark.parametrize("value", [-1, 101, float("nan"), float("inf")])
def test_invalid_preferences_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        select_model(
            predictions(),
            {"cheap": 0.01, "strong": 0.10},
            lambda_penalty=3,
            cost_saving_preference=value,
        )
