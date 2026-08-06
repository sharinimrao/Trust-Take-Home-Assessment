from __future__ import annotations

import pytest

from take_home_router.schemas import PromptMetadata, RouteRequest
from take_home_router.service import ClassifierService, RoutingRequestError


def test_service_returns_selected_model_ranked_scores_and_explanations(
    service: ClassifierService,
) -> None:
    candidates = ["mistralai/mistral-7b-chat", "gpt-4-1106-preview"]
    request = RouteRequest(
        prompt="Implement an LRU cache in Python and explain the complexity.",
        metadata=PromptMetadata(
            candidate_models=candidates,
            cost_saving_preference=50,
            include_explanations=True,
            request_id="test-123",
        ),
    )

    result = service.route(request)

    assert result.request_id == "test-123"
    assert result.classifier == "s2-savings-router"
    assert result.selected_model in candidates
    assert [item.model for item in result.candidates]
    assert result.candidates[0].model == result.selected_model
    assert all(item.top_contributions is not None for item in result.candidates)
    assert all(len(item.top_contributions or []) == 5 for item in result.candidates)


def test_cost_only_policy_selects_the_cheapest_requested_candidate(
    service: ClassifierService,
) -> None:
    candidates = ["mistralai/mistral-7b-chat", "gpt-4-1106-preview"]
    result = service.route(
        RouteRequest(
            prompt="Say hello.",
            metadata=PromptMetadata(
                candidate_models=candidates,
                cost_saving_preference=100,
            ),
        )
    )

    assert result.selected_model == "mistralai/mistral-7b-chat"


def test_service_catalog_and_unknown_candidate(service: ClassifierService) -> None:
    catalog = service.catalog()
    assert catalog.select_only is True
    assert len(catalog.candidates) == 11

    with pytest.raises(RoutingRequestError, match="unknown candidate"):
        service.route(
            RouteRequest(
                prompt="hello",
                metadata=PromptMetadata(candidate_models=["unknown/model"]),
            )
        )
