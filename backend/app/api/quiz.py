from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, status

from backend.app.api.deps import public_question_payload, user_from_authorization
from backend.app.schemas import AnswerRequest, AnswerResult, QuestionDTO
from backend.app.services import InvalidAnswerIndexError, QuestionNotFoundError, QuizService


def create_quiz_router(service: QuizService) -> APIRouter:
    router = APIRouter(prefix="/quiz", tags=["quiz"])

    @router.get("/next", response_model=QuestionDTO)
    def next_question(authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        selection = service.next_question(user["id"])
        if selection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No question available")
        return public_question_payload(selection)

    @router.post("/answer", response_model=AnswerResult)
    def answer(req: AnswerRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
        user = user_from_authorization(service, authorization)
        try:
            return service.answer(user["id"], req.question_id, req.selected_index, req.elapsed_ms)
        except InvalidAnswerIndexError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except QuestionNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return router
