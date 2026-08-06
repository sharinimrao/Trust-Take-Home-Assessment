from __future__ import annotations

import math
from pathlib import Path

import pytest

from take_home_router.features import extract_prompt_features
from take_home_router.model import ArtifactError, S2Classifier

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = (
    "mistralai/mistral-7b-chat",
    "gpt-4-1106-preview",
)


@pytest.fixture(scope="module")
def classifier() -> S2Classifier:
    return S2Classifier(
        ROOT / "artifacts" / "s2",
        ROOT / "artifacts" / "auxiliary" / "a2_matrixfact.json",
    )


def test_actual_artifacts_load_with_expected_candidate_fleet(classifier: S2Classifier) -> None:
    assert len(classifier.candidates) == 11
    assert set(CANDIDATES) <= set(classifier.candidates)
    assert len(classifier.feature_names) == 52


def test_prediction_is_deterministic_auditable_and_bounded(classifier: S2Classifier) -> None:
    prompt = "Write a Python merge sort and explain its complexity."

    first = classifier.predict_prompt(prompt, CANDIDATES)
    second = classifier.predict_prompt(prompt, CANDIDATES)

    assert first == second
    assert list(first) == list(CANDIDATES)
    for candidate, prediction in first.items():
        assert prediction.candidate == candidate
        assert 0.0 <= prediction.quality <= 1.0
        assert 0.0 <= prediction.raw_quality <= 1.0
        assert prediction.expected_output_tokens >= 0
        assert 0.0 <= prediction.uncertainty <= 0.5
        assert len(prediction.contributions) == 53
        assert "a2_score" in prediction.contributions
        assert "bias" in prediction.contributions


def test_golden_predictions_match_the_original_trustrouter_s2(classifier: S2Classifier) -> None:
    predictions = classifier.predict_prompt(
        "Write a Python merge sort and explain its complexity.",
        CANDIDATES,
    )

    cheap = predictions["mistralai/mistral-7b-chat"]
    strong = predictions["gpt-4-1106-preview"]
    assert math.isclose(cheap.quality, 0.1677937761344669, rel_tol=1e-15)
    assert math.isclose(cheap.raw_quality, 0.18723497124748825, rel_tol=1e-15)
    assert cheap.expected_output_tokens == 29
    assert math.isclose(strong.quality, 0.27263987322772393, rel_tol=1e-15)
    assert math.isclose(strong.raw_quality, 0.32439400339447483, rel_tol=1e-15)
    assert strong.expected_output_tokens == 81


def test_prompt_and_precomputed_feature_paths_are_equivalent(classifier: S2Classifier) -> None:
    prompt = "Prove that there are infinitely many prime numbers."

    direct = classifier.predict_prompt(prompt, CANDIDATES)
    precomputed = classifier.predict_features(extract_prompt_features(prompt), CANDIDATES)

    assert direct == precomputed


def test_unknown_candidate_fails_closed(classifier: S2Classifier) -> None:
    with pytest.raises(ArtifactError, match="missing S2 candidate"):
        classifier.predict_prompt("hello", ["not-a-real-model"])


def test_missing_artifact_fails_during_startup(tmp_path: Path) -> None:
    with pytest.raises(ArtifactError, match="metadata"):
        S2Classifier(tmp_path, ROOT / "artifacts" / "auxiliary" / "a2_matrixfact.json")
