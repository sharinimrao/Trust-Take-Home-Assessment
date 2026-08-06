"""Application service joining feature extraction, inference, and selection."""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

from take_home_router.config import RouterConfig
from take_home_router.model import ModelPrediction, S2Classifier
from take_home_router.policy import ScoredCandidate, select_model
from take_home_router.schemas import (
    CandidateResult,
    FeatureContribution,
    HealthResponse,
    ModelCatalogResponse,
    PolicyResult,
    RouteRequest,
    RouteResponse,
)

_PACKAGE_ROOT = Path(__file__).resolve().parent
_REPOSITORY_ROOT = _PACKAGE_ROOT.parents[1]


class RoutingRequestError(ValueError):
    """Raised when request metadata cannot be served by this classifier."""


class ClassifierService:
    """Thread-safe, select-only prompt router with immutable loaded artifacts."""

    def __init__(self, classifier: S2Classifier, config: RouterConfig) -> None:
        config.validate_candidates(classifier.candidates)
        self.classifier = classifier
        self.config = config
        self._prediction_lock = threading.RLock()

    @classmethod
    def from_paths(
        cls,
        *,
        s2_artifact_dir: Path,
        auxiliary_artifact: Path,
        config_path: Path,
    ) -> ClassifierService:
        return cls(
            S2Classifier(s2_artifact_dir, auxiliary_artifact),
            RouterConfig.load(config_path),
        )

    @classmethod
    def from_environment(cls) -> ClassifierService:
        return cls.from_paths(
            s2_artifact_dir=_environment_path(
                "ROUTER_S2_ARTIFACT_DIR",
                _bundled_path("artifacts", "s2"),
            ),
            auxiliary_artifact=_environment_path(
                "ROUTER_AUXILIARY_ARTIFACT",
                _bundled_path("artifacts", "auxiliary", "a2_matrixfact.json"),
            ),
            config_path=_environment_path(
                "ROUTER_CONFIG",
                _bundled_path("config", "router.json"),
            ),
        )

    def route(self, request: RouteRequest) -> RouteResponse:
        started = time.perf_counter()
        metadata = request.metadata
        candidates = tuple(metadata.candidate_models or self.classifier.candidates)
        unknown = sorted(set(candidates) - set(self.classifier.candidates))
        if unknown:
            raise RoutingRequestError(f"unknown candidate models: {unknown}")
        preference = (
            self.config.default_cost_saving_preference
            if metadata.cost_saving_preference is None
            else metadata.cost_saving_preference
        )
        with self._prediction_lock:
            predictions = self.classifier.predict_prompt(request.prompt, candidates)
        selection = select_model(
            predictions,
            self.config.mean_cost_usd,
            lambda_penalty=self.config.lambda_penalty,
            cost_saving_preference=preference,
        )
        results = [
            self._candidate_result(
                score.model,
                predictions[score.model],
                score,
                metadata.include_explanations,
            )
            for score in selection.candidates
        ]
        latency_ms = (time.perf_counter() - started) * 1_000.0
        return RouteResponse(
            request_id=metadata.request_id or str(uuid.uuid4()),
            classifier=self.config.classifier_name,
            classifier_version=self.config.classifier_version,
            selected_model=selection.selected_model,
            routing_latency_ms=latency_ms,
            policy=PolicyResult(
                cost_saving_preference=selection.cost_saving_preference,
                quality_weight=selection.quality_weight,
                cost_weight=selection.cost_weight,
                lambda_penalty=selection.lambda_penalty,
            ),
            candidates=results,
        )

    def catalog(self) -> ModelCatalogResponse:
        return ModelCatalogResponse(
            classifier=self.config.classifier_name,
            classifier_version=self.config.classifier_version,
            candidates=list(self.classifier.candidates),
            default_cost_saving_preference=self.config.default_cost_saving_preference,
        )

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            classifier_loaded=True,
            candidate_count=len(self.classifier.candidates),
        )

    @staticmethod
    def _candidate_result(
        model: str,
        prediction: ModelPrediction,
        score: ScoredCandidate,
        include_explanations: bool,
    ) -> CandidateResult:
        explanations: list[FeatureContribution] | None = None
        if include_explanations:
            ranked = sorted(
                (
                    (name, value)
                    for name, value in prediction.contributions.items()
                    if name != "bias"
                ),
                key=lambda item: (-abs(item[1]), item[0]),
            )[:5]
            explanations = [FeatureContribution(name=name, value=value) for name, value in ranked]
        return CandidateResult(
            model=model,
            predicted_quality=score.predicted_quality,
            expected_output_tokens=score.expected_output_tokens,
            uncertainty=score.uncertainty,
            benchmark_mean_cost_usd=score.benchmark_mean_cost_usd,
            quality_component=score.quality_component,
            cost_penalty=score.cost_penalty,
            utility=score.utility,
            top_contributions=explanations,
        )


def _bundled_path(*parts: str) -> Path:
    repository_path = _REPOSITORY_ROOT.joinpath(*parts)
    if repository_path.exists():
        return repository_path
    return _PACKAGE_ROOT.joinpath(*parts)


def _environment_path(name: str, default: Path) -> Path:
    configured = os.environ.get(name)
    return Path(configured) if configured else default
