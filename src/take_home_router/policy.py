"""Transparent quality-versus-cost selection over classifier predictions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol


class PredictionLike(Protocol):
    @property
    def candidate(self) -> str: ...

    @property
    def quality(self) -> float: ...

    @property
    def expected_output_tokens(self) -> int: ...

    @property
    def uncertainty(self) -> float: ...


class RandomSource(Protocol):
    """Minimal random interface used by the exploration policy."""

    def random(self) -> float: ...

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int: ...


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    model: str
    predicted_quality: float
    expected_output_tokens: int
    uncertainty: float
    benchmark_mean_cost_usd: float
    quality_component: float
    cost_penalty: float
    utility: float


@dataclass(frozen=True, slots=True)
class Selection:
    selected_model: str
    selection_mode: Literal["scored", "random"]
    random_selection_probability: float
    cost_saving_preference: float
    quality_weight: float
    cost_weight: float
    lambda_penalty: float
    candidates: tuple[ScoredCandidate, ...]


def select_model(
    predictions: Mapping[str, PredictionLike],
    mean_cost_usd: Mapping[str, float],
    *,
    lambda_penalty: float,
    cost_saving_preference: float,
    random_selection_probability: float = 0.0,
    random_source: RandomSource | None = None,
) -> Selection:
    """Rank candidates and optionally replace the winner with uniform exploration.

    At preference 50, multiplying both objective terms by 0.5 leaves the exact
    benchmark ordering ``quality - lambda * mean_cost`` unchanged. The endpoints
    expose quality-only and cost-only decisions without retraining the classifier.
    """

    if not predictions:
        raise ValueError("at least one candidate prediction is required")
    preference = _percentage(cost_saving_preference)
    penalty = _nonnegative(lambda_penalty, "lambda_penalty")
    exploration_probability = _probability(random_selection_probability)
    quality_weight = 1.0 - preference
    cost_weight = preference
    scores: list[ScoredCandidate] = []
    for model, prediction in predictions.items():
        if model != prediction.candidate:
            raise ValueError(f"prediction key {model!r} does not match its candidate")
        quality = float(prediction.quality)
        if not math.isfinite(quality) or not 0.0 <= quality <= 1.0:
            raise ValueError(f"invalid predicted quality for {model!r}")
        uncertainty = _nonnegative(prediction.uncertainty, f"uncertainty[{model!r}]")
        tokens = prediction.expected_output_tokens
        if tokens < 0:
            raise ValueError(f"invalid expected output tokens for {model!r}")
        if model not in mean_cost_usd:
            raise ValueError(f"missing benchmark mean cost for {model!r}")
        cost = _nonnegative(mean_cost_usd[model], f"mean_cost_usd[{model!r}]")
        quality_component = quality_weight * quality
        cost_penalty = cost_weight * penalty * cost
        scores.append(
            ScoredCandidate(
                model=model,
                predicted_quality=quality,
                expected_output_tokens=tokens,
                uncertainty=uncertainty,
                benchmark_mean_cost_usd=cost,
                quality_component=quality_component,
                cost_penalty=cost_penalty,
                utility=quality_component - cost_penalty,
            )
        )
    scored = tuple(
        sorted(scores, key=lambda item: (-item.utility, item.benchmark_mean_cost_usd, item.model))
    )
    selection_mode: Literal["scored", "random"] = "scored"
    selected_model = scored[0].model
    ranked = scored
    if exploration_probability > 0.0:
        if random_source is None:
            raise ValueError("random_source is required when random selection is enabled")
        exploration_draw = random_source.random()
        if not math.isfinite(exploration_draw) or not 0.0 <= exploration_draw < 1.0:
            raise ValueError("random_source returned a draw outside [0, 1)")
        if exploration_draw < exploration_probability:
            selection_mode = "random"
            selected_index = random_source.randrange(len(scored))
            if not 0 <= selected_index < len(scored):
                raise ValueError("random_source returned an out-of-range candidate index")
            selected = scored[selected_index]
            selected_model = selected.model
            ranked = (selected, *(candidate for candidate in scored if candidate is not selected))
    return Selection(
        selected_model=selected_model,
        selection_mode=selection_mode,
        random_selection_probability=exploration_probability,
        cost_saving_preference=cost_saving_preference,
        quality_weight=quality_weight,
        cost_weight=cost_weight,
        lambda_penalty=penalty,
        candidates=ranked,
    )


def _percentage(value: object) -> float:
    parsed = _nonnegative(value, "cost_saving_preference")
    if parsed > 100.0:
        raise ValueError("cost_saving_preference must be between 0 and 100")
    return parsed / 100.0


def _probability(value: object) -> float:
    parsed = _nonnegative(value, "random_selection_probability")
    if parsed > 1.0:
        raise ValueError("random_selection_probability must be between 0 and 1")
    return parsed


def _nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return parsed
