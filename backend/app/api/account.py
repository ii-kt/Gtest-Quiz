from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header

from backend.app.api.deps import user_from_authorization
from backend.app.schemas import ImportBundleRequest, ImportBundleResult
from backend.app.services import QuizService


def create_account_router(service: QuizService) -> APIRouter:
    router = APIRouter(prefix="/account", tags=["account"])

    @router.get("/export")
    def export_account(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.export_account(int(user["id"]))

    @router.post("/import", response_model=ImportBundleResult)
    def import_account(req: ImportBundleRequest, authorization: str = Header(default="")) -> Dict[str, int]:
        user = user_from_authorization(service, authorization)
        return service.import_account(int(user["id"]), req.bundle)

    @router.get("/audit")
    def audit_log(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        return service.audit_log(int(user["id"]))

    return router
