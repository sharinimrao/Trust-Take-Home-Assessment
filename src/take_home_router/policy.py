"""Transparent quality-versus-cost selection over classifier predictions."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class PredictionLike(Protocol):
    @property
    def candidate(self) -> str: ...

    @property
    def quality(self) -> float: ...

    @property
    def expected_output_tokens(self) -> int: ...

    @property
    def uncertainty(self) -> float: ...


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
) -> Selection:
    """Rank candidates with the benchmark policy and deterministic tie-breaking.

    At preference 50, multiplying both objective terms by 0.5 leaves the exact
    benchmark ordering ``quality - lambda * mean_cost`` unchanged. The endpoints
    expose quality-only and cost-only decisions without retraining the classifier.
    """

    if not predictions:
        raise ValueError("at least one candidate prediction is required")
    preference = _percentage(cost_saving_preference)
    penalty = _nonnegative(lambda_penalty, "lambda_penalty")
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
    ranked = tuple(
        sorted(scores, key=lambda item: (-item.utility, item.benchmark_mean_cost_usd, item.model))
    )
    return Selection(
        selected_model=ranked[0].model,
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


def _nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return parsed
