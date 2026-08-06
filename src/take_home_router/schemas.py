"""Public HTTP request and response contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromptMetadata(BaseModel):
    """Optional routing controls supplied alongside a prompt."""

    model_config = ConfigDict(extra="forbid")

    candidate_models: list[str] | None = Field(
        default=None,
        min_length=1,
        description="Optional subset of classifier candidates to consider.",
    )
    cost_saving_preference: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="0 selects by quality; 100 selects by cost; 50 is benchmark-tuned.",
    )
    include_explanations: bool = Field(
        default=False,
        description="Return the five largest per-candidate feature contributions.",
    )
    request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("candidate_models")
    @classmethod
    def validate_candidates(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [candidate.strip() for candidate in value]
        if any(not candidate for candidate in cleaned):
            raise ValueError("candidate model IDs must be non-empty")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("candidate model IDs must be unique")
        return cleaned


class RouteRequest(BaseModel):
    """One prompt and its optional routing metadata."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=200_000)
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt must contain non-whitespace text")
        return value


class FeatureContribution(BaseModel):
    name: str
    value: float


class CandidateResult(BaseModel):
    model: str
    predicted_quality: float = Field(ge=0.0, le=1.0)
    expected_output_tokens: int = Field(ge=0)
    uncertainty: float = Field(ge=0.0)
    benchmark_mean_cost_usd: float = Field(ge=0.0)
    quality_component: float
    cost_penalty: float = Field(ge=0.0)
    utility: float
    top_contributions: list[FeatureContribution] | None = None


class PolicyResult(BaseModel):
    cost_saving_preference: float = Field(ge=0.0, le=100.0)
    quality_weight: float = Field(ge=0.0, le=1.0)
    cost_weight: float = Field(ge=0.0, le=1.0)
    lambda_penalty: float = Field(ge=0.0)


class RouteResponse(BaseModel):
    request_id: str
    classifier: str
    classifier_version: str
    selected_model: str
    routing_latency_ms: float = Field(ge=0.0)
    policy: PolicyResult
    candidates: list[CandidateResult]


class ModelCatalogResponse(BaseModel):
    classifier: str
    classifier_version: str
    candidates: list[str]
    default_cost_saving_preference: float
    select_only: bool = True


class HealthResponse(BaseModel):
    status: str
    classifier_loaded: bool
    candidate_count: int = Field(ge=0)
