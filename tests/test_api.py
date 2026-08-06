# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from fastapi.testclient import TestClient

from take_home_router.api import create_app
from take_home_router.service import ClassifierService


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
