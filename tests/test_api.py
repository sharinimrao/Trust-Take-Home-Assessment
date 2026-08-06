# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from fastapi.testclient import TestClient

from take_home_router.api import create_app
from take_home_router.service import ClassifierService


class AlwaysExploreSecondCandidate:
    def random(self) -> float:
        return 0.0

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        assert stop is None
        assert step == 1
        assert start >= 2
        return 1


def test_http_health_catalog_and_route(service: ClassifierService) -> None:
    with TestClient(create_app(service)) as client:
        health = client.get("/healthz")
        catalog = client.get("/v1/models")
        routed = client.post(
            "/v1/route",
            json={
                "prompt": "Write a SQL query that finds duplicate email addresses.",
                "metadata": {
                    "candidate_models": [
                        "mistralai/mistral-7b-chat",
                        "gpt-4-1106-preview",
                    ],
                    "cost_saving_preference": 50,
                    "request_id": "api-test",
                },
            },
        )

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "classifier_loaded": True,
        "candidate_count": 11,
    }
    assert catalog.status_code == 200
    assert catalog.json()["select_only"] is True
    assert routed.status_code == 200
    body = routed.json()
    assert body["request_id"] == "api-test"
    assert body["selected_model"] in {
        "mistralai/mistral-7b-chat",
        "gpt-4-1106-preview",
    }
    assert body["policy"]["selection_mode"] == "scored"
    assert body["policy"]["random_selection_probability"] == 0.3
    assert catalog.json()["random_selection_probability"] == 0.3


def test_http_route_exposes_random_exploration(service: ClassifierService) -> None:
    exploring_service = ClassifierService(
        service.classifier,
        service.config,
        AlwaysExploreSecondCandidate(),
    )
    with TestClient(create_app(exploring_service)) as client:
        response = client.post(
            "/v1/route",
            json={
                "prompt": "Say hello.",
                "metadata": {
                    "candidate_models": [
                        "mistralai/mistral-7b-chat",
                        "gpt-4-1106-preview",
                    ],
                    "cost_saving_preference": 100,
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["selection_mode"] == "random"
    assert body["policy"]["random_selection_probability"] == 0.3
    assert body["selected_model"] == "gpt-4-1106-preview"
    assert body["candidates"][0]["model"] == body["selected_model"]


def test_http_contract_rejects_invalid_prompts_metadata_and_candidates(
    service: ClassifierService,
) -> None:
    with TestClient(create_app(service)) as client:
        blank = client.post("/v1/route", json={"prompt": "  "})
        extra = client.post(
            "/v1/route",
            json={"prompt": "hello", "metadata": {"not_supported": True}},
        )
        unknown = client.post(
            "/v1/route",
            json={"prompt": "hello", "metadata": {"candidate_models": ["unknown"]}},
        )

    assert blank.status_code == 422
    assert extra.status_code == 422
    assert unknown.status_code == 422
    assert "unknown candidate" in unknown.json()["detail"]
