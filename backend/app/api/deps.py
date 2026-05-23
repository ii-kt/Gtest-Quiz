from __future__ import annotations

from typing import Any, Dict

from fastapi import Header, HTTPException, status

from backend.app.services import QuizService, UnauthorizedError


def user_from_authorization(service: QuizService, authorization: str = Header(default="")) -> Dict[str, Any]:
    token = bearer_token_from_authorization(authorization)
    try:
        return service.user_from_token(token)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


def bearer_token_from_authorization(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return authorization.replace("Bearer ", "", 1).strip()


def public_question_payload(selection: Any) -> Dict[str, Any]:
    q = selection.question
    return {
        "id": q.id,
        "domain": q.domain,
        "chapter_group": q.chapter_group,
        "chapter_id": q.chapter_id,
        "difficulty": q.difficulty,
        "question": q.question,
        "choices": q.choices,
        "learning": selection.learning,
    }
