from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter

from backend.app.content import chapter_catalog, offline_question_pack, question_bank_summary


def create_content_router() -> APIRouter:
    router = APIRouter(prefix="/content", tags=["content"])

    @router.get("/chapters")
    def chapters() -> List[Dict[str, Any]]:
        return chapter_catalog()

    @router.get("/questions/summary")
    def question_summary() -> Dict[str, Any]:
        return question_bank_summary()

    @router.get("/offline-pack")
    def offline_pack() -> Dict[str, Any]:
        return offline_question_pack()

    return router
