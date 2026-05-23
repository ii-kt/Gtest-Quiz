from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.account import create_account_router
from backend.app.api.analytics import create_analytics_router
from backend.app.api.auth import create_auth_router
from backend.app.api.content import create_content_router
from backend.app.api.operations import create_operations_router
from backend.app.api.quiz import create_quiz_router
from backend.app.services import QuizService


def create_api_router(service: QuizService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_operations_router(service))
    router.include_router(create_auth_router(service))
    router.include_router(create_quiz_router(service))
    router.include_router(create_analytics_router(service))
    router.include_router(create_content_router())
    router.include_router(create_account_router(service))
    return router
