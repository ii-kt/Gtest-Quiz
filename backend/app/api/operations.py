from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header

from backend.app.api.deps import user_from_authorization
from backend.app.deployment import current_profile_name
from backend.app.services import QuizService


def create_operations_router(service: QuizService) -> APIRouter:
    router = APIRouter(tags=["operations"])

    @router.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok", "api_version": "v1", "deployment_profile": current_profile_name()}

    @router.get("/operations/metrics")
    def metrics(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.operations_metrics(int(user["id"]))

    return router
