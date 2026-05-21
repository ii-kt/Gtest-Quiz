from __future__ import annotations

import random
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import get_all_questions, get_question_by_id

from .storage import Storage


class InvalidAnswerIndexError(ValueError):
    pass


class QuestionNotFoundError(ValueError):
    pass


class UnauthorizedError(ValueError):
    pass


class UserAlreadyExistsError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


@dataclass
class QuizService:
    meta_path: str = "bank/meta.json"
    db_path: str = "backend/app/quiz.db"

    def __post_init__(self) -> None:
        self.meta = MetaManager(self.meta_path)
        self.meta.load()
        self.storage = Storage(self.db_path)

    def register(self, username: str) -> Dict[str, str]:
        if self.storage.get_user_by_username(username):
            raise UserAlreadyExistsError("username already exists")
        token = secrets.token_urlsafe(24)
        user = self.storage.create_user(username=username, token=token)
        return {"username": user["username"], "token": user["token"]}

    def login(self, username: str) -> Dict[str, str]:
        user = self.storage.get_user_by_username(username)
        if not user:
            raise UserNotFoundError("user not found")
        token = secrets.token_urlsafe(24)
        user = self.storage.rotate_token(user_id=int(user["id"]), token=token)
        return {"username": user["username"], "token": user["token"]}

    def user_from_token(self, token: str) -> Dict[str, Any]:
        user = self.storage.get_user_by_token(token)
        if not user:
            raise UnauthorizedError("invalid token")
        return user

    def _adaptive_candidates(self, user_id: int, bank: list[Question]) -> list[Question]:
        answered = set(self.storage.answered_question_ids(user_id))
        unseen = [q for q in bank if q.id not in answered]
        return unseen if unseen else bank

    def next_question(self, user_id: int) -> Optional[Question]:
        bank = get_all_questions()
        if not bank:
            return None

        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
        weak = user_stats.get("weak_chapters", [])
        weak_chapter = weak[0]["chapter_id"] if weak and weak[0].get("wrongs", 0) > 0 else None
        if weak_chapter:
            weak_candidates = [q for q in candidate_pool if q.chapter_id == weak_chapter]
            if weak_candidates:
                return random.choice(weak_candidates)

        chapter_ids = sorted({q.chapter_id for q in candidate_pool})
        chosen_chapter = self.meta.choose_next_chapter(chapter_ids)
        if chosen_chapter:
            candidates = [q for q in candidate_pool if q.chapter_id == chosen_chapter]
            if candidates:
                return random.choice(candidates)

        return random.choice(candidate_pool)

    def answer(self, user_id: int, question_id: str, selected_index: int) -> Dict[str, Any]:
        if selected_index not in {0, 1, 2, 3}:
            raise InvalidAnswerIndexError("selected_index must be 0..3")

        q = get_question_by_id(question_id)
        if q is None:
            raise QuestionNotFoundError("question_id not found")

        correct = q.is_correct(selected_index)
        self.meta.record_usage(q.chapter_id, "offline")
        self.meta.save()
        self.storage.record_answer(user_id, q.id, q.chapter_id, selected_index, correct)

        return {
            "correct": correct,
            "correct_index": q.correct_index,
            "explanation": q.explanation,
        }

    def stats(self, user_id: int) -> Dict[str, Any]:
        usage = self.meta.meta.get("usage", {})
        return {
            "global": {
                "total_questions": int(usage.get("total_questions", 0)),
                "online_questions": int(usage.get("online_questions", 0)),
                "offline_questions": int(usage.get("offline_questions", 0)),
            },
            "user": self.storage.user_stats(user_id),
        }
