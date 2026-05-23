from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header

from backend.app.api.deps import bearer_token_from_authorization, user_from_authorization
from backend.app.schemas import AccountProfile, LogoutResponse, SessionResponse, StartSessionRequest
from backend.app.services import QuizService


def create_auth_router(service: QuizService) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/start", response_model=SessionResponse)
    def start(req: StartSessionRequest) -> Dict[str, Any]:
        return service.start_session(req.display_name)

    @router.post("/refresh", response_model=SessionResponse)
    def refresh(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.refresh_session(int(user["id"]))

    @router.get("/me", response_model=AccountProfile)
    def me(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.account_profile(int(user["id"]))

    @router.post("/logout", response_model=LogoutResponse)
    def logout(authorization: str = Header(default="")) -> Dict[str, bool]:
        token = bearer_token_from_authorization(authorization)
        return service.logout(token)

    return router
