# pyright: reportUnusedFunction=false
"""FastAPI delivery surface for the select-only model classifier."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from take_home_router.schemas import (
    HealthResponse,
    ModelCatalogResponse,
    RouteRequest,
    RouteResponse,
)
from take_home_router.service import ClassifierService, RoutingRequestError


def create_app(service: ClassifierService | None = None) -> FastAPI:
    """Create an app, loading model artifacts exactly once during startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        app.state.classifier_service = service or ClassifierService.from_environment()
        yield

    app = FastAPI(
        title="Take Home Model Router",
        version="1.0.0",
        summary="Classify a prompt into the generation model that should handle it.",
        description=(
            "A select-only API around the calibrated S2 classifier. It returns a model ID "
            "and never invokes a generation provider."
        ),
        lifespan=lifespan,
    )

    # The router ships with no frontend of its own, so CORS is wide open by
    # default to unblock local development. Tighten `allow_origins` to the
    # deployed frontend origin(s) before shipping this anywhere real.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/healthz", response_model=HealthResponse, tags=["operations"])
    def health(request: Request) -> HealthResponse:
        return _service(request).health()

    @app.get("/v1/models", response_model=ModelCatalogResponse, tags=["routing"])
    def models(request: Request) -> ModelCatalogResponse:
        return _service(request).catalog()

    @app.post(
        "/v1/route",
        response_model=RouteResponse,
        tags=["routing"],
        responses={422: {"description": "Invalid prompt or unsupported candidate model."}},
    )
    def route(payload: RouteRequest, request: Request) -> RouteResponse:
        try:
            return _service(request).route(payload)
        except RoutingRequestError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


def _service(request: Request) -> ClassifierService:
    value = request.app.state.classifier_service
    if not isinstance(value, ClassifierService):
        raise RuntimeError("classifier service was not initialized")
    return value


app = create_app()
