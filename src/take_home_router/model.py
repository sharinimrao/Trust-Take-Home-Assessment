# pyright: reportUnknownMemberType=false
"""Isolated inference implementation for the calibrated S2 model router.

This module intentionally contains only the model. It does not import TrustRouter's
registry, gateway, dashboard, proxy, benchmark harness, or hybrid quality router.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, cast

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray

from take_home_router.features import EMBEDDING_DIMENSIONS, PromptFeatures, extract_prompt_features

LATENT_DIMENSIONS = 32
CalibrationKind = Literal["affine", "platt"]


class ArtifactError(RuntimeError):
    """Raised when model artifacts are missing, malformed, or incompatible."""


@dataclass(frozen=True, slots=True)
class ModelPrediction:
    candidate: str
    quality: float
    expected_output_tokens: int
    uncertainty: float
    raw_quality: float
    contributions: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class _Calibration:
    kind: CalibrationKind
    a: float
    b: float
    sigma: float | None


@dataclass(frozen=True, slots=True)
class _CandidateArtifacts:
    quality: lgb.Booster
    tokens: lgb.Booster
    calibration: _Calibration


@dataclass(frozen=True, slots=True)
class _AuxiliaryModel:
    prompt_projection: NDArray[np.float64]
    model_vectors: Mapping[str, NDArray[np.float64]]
    model_biases: Mapping[str, float]
    global_bias: float

    @classmethod
    def load(cls, path: Path, candidates: Sequence[str]) -> _AuxiliaryModel:
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("root must be an object")
            payload = cast(dict[str, object], raw)
            raw_metadata = payload.get("metadata")
            if not isinstance(raw_metadata, dict):
                raise ValueError("metadata must be an object")
            metadata = cast(dict[str, object], raw_metadata)
            if metadata.get("format") != "a2_matrixfact.v1":
                raise ValueError("unsupported auxiliary format")
            if metadata.get("latent_dim") != LATENT_DIMENSIONS:
                raise ValueError("auxiliary latent dimension must be 32")
            projection = np.asarray(payload["prompt_projection"], dtype=np.float64)
            if projection.shape != (EMBEDDING_DIMENSIONS, LATENT_DIMENSIONS):
                raise ValueError("prompt_projection must be shaped 48x32")
            if not bool(np.isfinite(projection).all()):
                raise ValueError("prompt_projection must contain finite values")
            vectors_value = payload.get("model_vectors")
            biases_value = payload.get("model_biases")
            if not isinstance(vectors_value, dict) or not isinstance(biases_value, dict):
                raise ValueError("model_vectors and model_biases must be objects")
            raw_vectors = cast(dict[str, object], vectors_value)
            raw_biases = cast(dict[str, object], biases_value)
            vectors: dict[str, NDArray[np.float64]] = {}
            biases: dict[str, float] = {}
            for candidate in candidates:
                vector = np.asarray(raw_vectors.get(candidate), dtype=np.float64)
                if vector.shape != (LATENT_DIMENSIONS,) or not bool(np.isfinite(vector).all()):
                    raise ValueError(f"invalid model vector for {candidate!r}")
                vectors[candidate] = vector
                biases[candidate] = _finite_float(raw_biases.get(candidate), f"bias[{candidate!r}]")
            global_bias = _finite_float(payload.get("global_bias", 0.0), "global_bias")
            return cls(
                prompt_projection=projection,
                model_vectors=MappingProxyType(vectors),
                model_biases=MappingProxyType(biases),
                global_bias=global_bias,
            )
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid auxiliary artifact {path}: {exc}") from exc

    def scores(self, embedding: Sequence[float], candidates: Sequence[str]) -> dict[str, float]:
        vector = np.asarray(embedding, dtype=np.float64)
        if vector.shape != (EMBEDDING_DIMENSIONS,) or not bool(np.isfinite(vector).all()):
            raise ValueError("prompt embedding must contain exactly 48 finite values")
        latent = vector @ self.prompt_projection
        return {
            candidate: max(
                -30.0,
                min(
                    30.0,
                    float(
                        latent @ self.model_vectors[candidate]
                        + self.model_biases[candidate]
                        + self.global_bias
                    ),
                ),
            )
            for candidate in candidates
        }


class S2Classifier:
    """Loaded calibrated per-candidate LightGBM classifier. Construction never trains."""

    def __init__(self, s2_artifact_dir: str | Path, auxiliary_artifact: str | Path) -> None:
        self.artifact_dir = Path(s2_artifact_dir)
        metadata = self._load_metadata(self.artifact_dir / "metadata.json")
        self.candidates = self._candidate_ids(metadata)
        self.feature_names = self._feature_names(metadata)
        self.scalar_features = self._scalar_features(metadata)
        self.embedding_feature = self._embedding_feature(metadata)
        self._validate_metadata(metadata)
        self._auxiliary = _AuxiliaryModel.load(Path(auxiliary_artifact), self.candidates)
        self._models = MappingProxyType(
            {candidate: self._load_candidate(candidate) for candidate in self.candidates}
        )

    def predict_prompt(
        self, prompt: str, candidates: Sequence[str] | None = None
    ) -> dict[str, ModelPrediction]:
        return self.predict_features(extract_prompt_features(prompt), candidates)

    def predict_features(
        self,
        features: PromptFeatures,
        candidates: Sequence[str] | None = None,
    ) -> dict[str, ModelPrediction]:
        selected = tuple(dict.fromkeys(candidates or self.candidates))
        if not selected:
            raise ValueError("at least one candidate is required")
        if any(not candidate for candidate in selected):
            raise ValueError("candidate IDs must be non-empty")
        unknown = sorted(set(selected) - set(self.candidates))
        if unknown:
            raise ArtifactError(f"missing S2 candidate artifacts for: {unknown}")
        auxiliary_scores = self._auxiliary.scores(features.emb, selected)
        return {
            candidate: self._predict_candidate(features, candidate, auxiliary_scores[candidate])
            for candidate in selected
        }

    def _predict_candidate(
        self, features: PromptFeatures, candidate: str, auxiliary_score: float
    ) -> ModelPrediction:
        values: dict[str, float] = {
            "a2_score": auxiliary_score,
            "has_code_fence": float(features.has_code_fence),
            "prompt_approx_tokens": float(features.prompt_approx_tokens),
            "prompt_chars": float(features.prompt_chars),
        }
        row = [values[name] for name in self.scalar_features]
        if len(features.emb) != EMBEDDING_DIMENSIONS or not all(
            math.isfinite(value) for value in features.emb
        ):
            raise ValueError("prompt embedding must contain exactly 48 finite values")
        row.extend(features.emb)
        matrix = np.asarray([row], dtype=np.float64)
        artifacts = self._models[candidate]
        contribution_output = np.asarray(
            cast(Any, artifacts.quality.predict(matrix, pred_contrib=True)),
            dtype=np.float64,
        )
        if contribution_output.ndim != 2 or contribution_output.shape[0] != 1:
            raise ArtifactError(f"invalid quality contribution matrix for {candidate!r}")
        raw_contributions = contribution_output[0]
        if raw_contributions.shape != (len(self.feature_names) + 1,) or not bool(
            np.isfinite(raw_contributions).all()
        ):
            raise ArtifactError(f"invalid quality contributions for {candidate!r}")
        raw_score = float(np.sum(raw_contributions))
        calibration = artifacts.calibration
        if calibration.kind == "platt":
            raw_quality = _sigmoid(raw_score)
            quality = _apply_platt(raw_quality, calibration.a, calibration.b)
            uncertainty = math.sqrt(max(quality * (1.0 - quality), 1e-6))
        else:
            raw_quality = raw_score
            quality = min(max(calibration.a * raw_score + calibration.b, 0.0), 1.0)
            uncertainty = (
                calibration.sigma
                if calibration.sigma is not None
                else math.sqrt(max(quality * (1.0 - quality), 1e-6))
            )
        token_output = np.asarray(
            cast(Any, artifacts.tokens.predict(matrix)),
            dtype=np.float64,
        )
        if token_output.shape != (1,):
            raise ArtifactError(f"invalid output-token prediction shape for {candidate!r}")
        token_value = float(token_output[0])
        if not math.isfinite(token_value):
            raise ArtifactError(f"invalid output-token prediction for {candidate!r}")
        contributions = MappingProxyType(
            dict(
                zip(
                    (*self.feature_names, "bias"),
                    (float(value) for value in raw_contributions),
                    strict=True,
                )
            )
        )
        return ModelPrediction(
            candidate=candidate,
            quality=min(max(quality, 0.0), 1.0),
            expected_output_tokens=max(0, round(max(0.0, token_value))),
            uncertainty=uncertainty,
            raw_quality=raw_quality,
            contributions=contributions,
        )

    def _load_candidate(self, candidate: str) -> _CandidateArtifacts:
        directory = self.artifact_dir / _safe_candidate(candidate)
        quality_path = directory / "quality.txt"
        tokens_path = directory / "tokens.txt"
        calibration_path = directory / "calibration.json"
        missing = [
            path for path in (quality_path, tokens_path, calibration_path) if not path.is_file()
        ]
        if missing:
            raise ArtifactError(f"missing artifacts for candidate {candidate!r}: {missing}")
        try:
            quality = lgb.Booster(model_file=str(quality_path))
            tokens = lgb.Booster(model_file=str(tokens_path))
            if tuple(quality.feature_name()) != self.feature_names:
                raise ValueError("quality model feature schema differs from metadata")
            if tuple(tokens.feature_name()) != self.feature_names:
                raise ValueError("token model feature schema differs from metadata")
            raw: object = json.loads(calibration_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("calibration must be an object")
            payload = cast(dict[str, object], raw)
            kind = payload.get("kind")
            if kind not in {"affine", "platt"}:
                raise ValueError("calibration kind must be affine or platt")
            sigma_raw = payload.get("sigma")
            sigma = None if sigma_raw is None else _finite_float(sigma_raw, "sigma")
            if sigma is not None and not 0.0 <= sigma <= 0.5:
                raise ValueError("calibration sigma must be in [0, 0.5]")
            calibration = _Calibration(
                kind=cast(CalibrationKind, kind),
                a=_finite_float(payload.get("a"), "a"),
                b=_finite_float(payload.get("b"), "b"),
                sigma=sigma,
            )
            return _CandidateArtifacts(quality=quality, tokens=tokens, calibration=calibration)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid artifacts for candidate {candidate!r}: {exc}") from exc

    @staticmethod
    def _load_metadata(path: Path) -> Mapping[str, object]:
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("metadata must be an object")
            return cast(dict[str, object], raw)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid S2 metadata artifact {path}: {exc}") from exc

    @staticmethod
    def _candidate_ids(metadata: Mapping[str, object]) -> tuple[str, ...]:
        raw: object = metadata.get("candidates")
        if not isinstance(raw, list):
            raise ArtifactError("metadata candidates must be non-empty model IDs")
        values = cast(list[object], raw)
        if not values or not all(isinstance(value, str) and value for value in values):
            raise ArtifactError("metadata candidates must be non-empty model IDs")
        candidates = tuple(cast(str, value) for value in values)
        if len(set(candidates)) != len(candidates):
            raise ArtifactError("metadata candidates must be unique")
        return candidates

    @staticmethod
    def _feature_names(metadata: Mapping[str, object]) -> tuple[str, ...]:
        raw: object = metadata.get("feature_names")
        if not isinstance(raw, list):
            raise ArtifactError("metadata feature_names must be strings")
        values = cast(list[object], raw)
        if not all(isinstance(value, str) for value in values):
            raise ArtifactError("metadata feature_names must be strings")
        return tuple(cast(str, value) for value in values)

    @staticmethod
    def _scalar_features(metadata: Mapping[str, object]) -> tuple[str, ...]:
        raw: object = metadata.get("scalar_features")
        if not isinstance(raw, list):
            raise ArtifactError("metadata scalar_features must be strings")
        values = cast(list[object], raw)
        if not all(isinstance(value, str) for value in values):
            raise ArtifactError("metadata scalar_features must be strings")
        return tuple(cast(str, value) for value in values)

    @staticmethod
    def _embedding_feature(metadata: Mapping[str, object]) -> str:
        raw: object = metadata.get("embedding_feature")
        if not isinstance(raw, str) or not raw:
            raise ArtifactError("metadata embedding_feature must be a string")
        return raw

    def _validate_metadata(self, metadata: Mapping[str, object]) -> None:
        if metadata.get("schema_version") not in {2, 3}:
            raise ArtifactError("unsupported S2 artifact schema version")
        if metadata.get("embedding_dimensions") != EMBEDDING_DIMENSIONS:
            raise ArtifactError("S2 embedding dimension must be 48")
        if self.embedding_feature != "emb":
            raise ArtifactError("bundled classifier requires the 'emb' embedding feature")
        expected_scalars = ("a2_score", "has_code_fence", "prompt_approx_tokens", "prompt_chars")
        if self.scalar_features != expected_scalars:
            raise ArtifactError("S2 scalar feature contract does not match the bundled extractor")
        if metadata.get("categorical_features") != []:
            raise ArtifactError("bundled classifier does not support categorical features")
        expected_names = (*expected_scalars, *(f"embedding_{index:02d}" for index in range(48)))
        if self.feature_names != expected_names:
            raise ArtifactError("S2 encoded feature names do not match metadata")


def _safe_candidate(candidate: str) -> str:
    safe = "".join(
        character if character.isalnum() or character in "._-" else "_" for character in candidate
    )
    if safe in {"", ".", ".."}:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:16]
        return f"candidate_{digest}"
    return safe


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        z = math.exp(-min(value, 700.0))
        return 1.0 / (1.0 + z)
    z = math.exp(max(value, -700.0))
    return z / (1.0 + z)


def _apply_platt(raw_quality: float, a: float, b: float) -> float:
    """Use the artifact's original probability-to-logit arithmetic exactly."""

    epsilon = 1e-12
    raw = min(max(raw_quality, epsilon), 1.0 - epsilon)
    logit = math.log(raw / (1.0 - raw))
    return _sigmoid(a * logit + b)
