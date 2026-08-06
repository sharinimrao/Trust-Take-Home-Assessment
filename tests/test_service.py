from __future__ import annotations

import pytest

from take_home_router.schemas import PromptMetadata, RouteRequest
from take_home_router.service import ClassifierService, RoutingRequestError


class AlwaysExploreSecondCandidate:
    def random(self) -> float:
        return 0.0

    def randrange(self, start: int, stop: int | None = None, step: int = 1) -> int:
        assert stop is None
        assert step == 1
        assert start >= 2
        return 1


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
    assert result.policy.selection_mode == "scored"
    assert result.policy.random_selection_probability == 0.3
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


def test_random_exploration_selects_an_eligible_non_winner_and_is_auditable(
    service: ClassifierService,
) -> None:
    exploring_service = ClassifierService(
        service.classifier,
        service.config,
        AlwaysExploreSecondCandidate(),
    )
    candidates = ["mistralai/mistral-7b-chat", "gpt-4-1106-preview"]

    result = exploring_service.route(
        RouteRequest(
            prompt="Say hello.",
            metadata=PromptMetadata(candidate_models=candidates, cost_saving_preference=100),
        )
    )

    assert result.policy.selection_mode == "random"
    assert result.policy.random_selection_probability == 0.3
    assert result.selected_model == "gpt-4-1106-preview"
    assert result.candidates[0].model == result.selected_model


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
