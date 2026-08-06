"""Validated runtime configuration for the standalone classifier."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast


class ConfigurationError(RuntimeError):
    """Raised when the checked-in router configuration is invalid."""


@dataclass(frozen=True, slots=True)
class RouterConfig:
    schema_version: int
    classifier_name: str
    classifier_version: str
    description: str
    lambda_penalty: float
    default_cost_saving_preference: float
    random_selection_probability: float
    mean_cost_usd: Mapping[str, float]
    benchmark: Mapping[str, object]

    @classmethod
    def load(cls, path: Path) -> RouterConfig:
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("root must be an object")
            payload = cast(dict[str, object], raw)
            schema_version = _integer(payload, "schema_version")
            if schema_version != 2:
                raise ValueError("schema_version must be 2")
            raw_costs = payload.get("mean_cost_usd")
            if not isinstance(raw_costs, dict) or not raw_costs:
                raise ValueError("mean_cost_usd must be a non-empty object")
            costs = {
                str(model): _nonnegative_float(value, f"mean_cost_usd[{model!r}]")
                for model, value in cast(dict[object, object], raw_costs).items()
            }
            if any(not model.strip() for model in costs):
                raise ValueError("mean_cost_usd model IDs must be non-empty")
            preference = _nonnegative_float(
                payload.get("default_cost_saving_preference"),
                "default_cost_saving_preference",
            )
            if preference > 100.0:
                raise ValueError("default_cost_saving_preference must be at most 100")
            random_selection_probability = _nonnegative_float(
                payload.get("random_selection_probability"),
                "random_selection_probability",
            )
            if random_selection_probability > 1.0:
                raise ValueError("random_selection_probability must be at most 1")
            benchmark = payload.get("benchmark", {})
            if not isinstance(benchmark, dict):
                raise ValueError("benchmark must be an object")
            return cls(
                schema_version=schema_version,
                classifier_name=_text(payload, "classifier_name"),
                classifier_version=_text(payload, "classifier_version"),
                description=_text(payload, "description"),
                lambda_penalty=_nonnegative_float(payload.get("lambda_penalty"), "lambda_penalty"),
                default_cost_saving_preference=preference,
                random_selection_probability=random_selection_probability,
                mean_cost_usd=MappingProxyType(costs),
                benchmark=MappingProxyType(cast(dict[str, object], benchmark)),
            )
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"invalid router configuration {path}: {exc}") from exc

    def validate_candidates(self, candidates: tuple[str, ...]) -> None:
        configured = set(self.mean_cost_usd)
        loaded = set(candidates)
        if configured != loaded:
            missing = sorted(loaded - configured)
            extra = sorted(configured - loaded)
            raise ConfigurationError(
                "configuration and model candidates differ: "
                f"missing_costs={missing}, unknown_costs={extra}"
            )


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _integer(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _nonnegative_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return parsed
