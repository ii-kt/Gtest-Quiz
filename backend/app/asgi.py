from __future__ import annotations

from fastapi import FastAPI
from fastapi import Request

from backend.app.api import create_api_router
from backend.app.observability import monotonic_ms, new_request_id, route_family
from backend.app.services import QuizService


def create_app(service: QuizService | None = None) -> FastAPI:
    api_service = service or QuizService()
    app = FastAPI(
        title="Gtest-Quiz API",
        version="0.2.0",
        description="Adaptive G検定 quiz API",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        started = monotonic_ms()
        response = await call_next(request)
        latency_ms = monotonic_ms() - started
        response.headers["X-Request-ID"] = request_id
        api_service.record_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            route_family=route_family(request.url.path),
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        return response

    app.include_router(create_api_router(api_service))
    return app


app = create_app()
