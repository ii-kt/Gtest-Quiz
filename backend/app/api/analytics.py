from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header

from backend.app.api.deps import user_from_authorization
from backend.app.schemas import PolicyPreferenceRequest, PolicyPreferenceResponse
from backend.app.services import QuizService


def create_analytics_router(service: QuizService) -> APIRouter:
    router = APIRouter(tags=["analytics"])

    @router.get("/quiz/stats")
    def quiz_stats(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.stats(user["id"])

    @router.get("/analytics/summary")
    def analytics_summary(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.stats(user["id"])["user"]

    @router.get("/learning/plan")
    def learning_plan(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.learning_plan(user["id"])

    @router.get("/learning/policy", response_model=PolicyPreferenceResponse)
    def get_learning_policy(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.get_policy(int(user["id"]))

    @router.post("/learning/policy", response_model=PolicyPreferenceResponse)
    def set_learning_policy(req: PolicyPreferenceRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.set_policy(int(user["id"]), req.policy_variant)

    return router
