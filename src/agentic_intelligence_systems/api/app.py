"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from agentic_intelligence_systems.api.dependencies import (
    ServiceContainer,
    build_service_container,
)
from agentic_intelligence_systems.api.routes import router
from agentic_intelligence_systems.config import get_settings
from agentic_intelligence_systems.observability.context import set_request_context
from agentic_intelligence_systems.observability.logging import configure_logging


def create_app(container: ServiceContainer | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = container.settings if container else get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_container = container or build_service_container(settings)
        app.state.container = runtime_container
        try:
            yield
        finally:
            await runtime_container.aclose()

    app = FastAPI(title=settings.app_name, version=settings.service_version, lifespan=lifespan)
    app.include_router(router)

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next,
    ):
        request_id, trace_id = set_request_context(
            request.headers.get(settings.request_header_name),
            request.headers.get(settings.trace_header_name),
        )
        response = await call_next(request)
        response.headers[settings.request_header_name] = request_id
        response.headers[settings.trace_header_name] = trace_id
        return response

    return app


app = create_app()
