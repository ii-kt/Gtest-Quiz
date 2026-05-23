from __future__ import annotations

import random
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
from backend.app.deployment import apply_profile_environment, configured_db_path, current_profile_name, load_deployment_profile
from backend.app.experiments import ADAPTIVE_POLICY, assign_policy_variant, experiment_summary, normalize_policy_variant
from backend.app.observability import structured_log
from backend.app.security import new_session_token, session_expiry
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import get_all_questions, get_question_by_id

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
from .learning import QuestionSelection, select_next_question, summarize_learning, update_schedule
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
from .storage import Storage


class InvalidAnswerIndexError(ValueError):
    pass


class QuestionNotFoundError(ValueError):
    pass


class UnauthorizedError(ValueError):
    pass


<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
@dataclass
class QuizService:
    meta_path: str = ".runtime/meta.json"
    db_path: str = ".runtime/quiz.db"

    def __post_init__(self) -> None:
        apply_profile_environment()
        if self.db_path == ".runtime/quiz.db":
            self.db_path = configured_db_path(self.db_path)
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
class UserAlreadyExistsError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


@dataclass
class QuizService:
    meta_path: str = "bank/meta.json"
    db_path: str = "backend/app/quiz.db"

    def __post_init__(self) -> None:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        self.meta = MetaManager(self.meta_path)
        self.meta.load()
        self.storage = Storage(self.db_path)

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    def _learner_id(self, user_id: int) -> str:
        return f"L{user_id:08d}"

    def start_session(self, display_name: Optional[str] = None) -> Dict[str, Any]:
        internal_key = f"learner_{secrets.token_hex(12)}"
        token = new_session_token()
        user = self.storage.create_user(
            account_key=internal_key,
            token=token,
            display_name=(display_name or "Learner").strip() or "Learner",
            session_expires_at=session_expiry(),
            policy_variant=ADAPTIVE_POLICY,
        )
        assigned_policy = self.storage.set_policy_variant(int(user["id"]), assign_policy_variant(int(user["id"]), internal_key))
        self.audit("auth.session.started", user_id=int(user["id"]), detail={"display_name": user.get("display_name", "")})
        return {
            "learner_id": self._learner_id(int(user["id"])),
            "display_name": user.get("display_name", "") or "Learner",
            "token": user["token"],
            "session_expires_at": user["session_expires_at"],
            "policy_variant": assigned_policy,
        }

    def refresh_session(self, user_id: int) -> Dict[str, Any]:
        user = self.storage.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedError("invalid or expired token")
        token = new_session_token()
        user = self.storage.rotate_token(user_id=user_id, token=token, session_expires_at=session_expiry())
        self.audit("auth.session.refreshed", user_id=user_id)
        return {
            "learner_id": self._learner_id(user_id),
            "display_name": user.get("display_name", "") or "Learner",
            "token": user["token"],
            "session_expires_at": user["session_expires_at"],
            "policy_variant": normalize_policy_variant(str(user.get("policy_variant", ""))),
        }
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
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
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs

    def user_from_token(self, token: str) -> Dict[str, Any]:
        user = self.storage.get_user_by_token(token)
        if not user:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            raise UnauthorizedError("invalid or expired token")
        return user

    def logout(self, token: str) -> Dict[str, Any]:
        user = self.storage.get_user_by_token(token)
        revoked = self.storage.revoke_session(token)
        if user:
            self.audit("auth.logout", user_id=int(user["id"]), detail={"revoked": revoked})
        return {"revoked": revoked}

    def account_profile(self, user_id: int) -> Dict[str, Any]:
        user = self.storage.get_user_by_id(user_id) or {}
        return {
            "user_id": user_id,
            "learner_id": self._learner_id(user_id),
            "display_name": user.get("display_name", "") or "Learner",
            "policy_variant": self.storage.get_policy_variant(user_id),
        }

=======
            raise UnauthorizedError("invalid token")
        return user

>>>>>>> theirs
=======
            raise UnauthorizedError("invalid token")
        return user

>>>>>>> theirs
=======
            raise UnauthorizedError("invalid token")
        return user

>>>>>>> theirs
=======
            raise UnauthorizedError("invalid token")
        return user

>>>>>>> theirs
=======
            raise UnauthorizedError("invalid token")
        return user

>>>>>>> theirs
    def _adaptive_candidates(self, user_id: int, bank: list[Question]) -> list[Question]:
        answered = set(self.storage.answered_question_ids(user_id))
        unseen = [q for q in bank if q.id not in answered]
        return unseen if unseen else bank

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    def next_question(self, user_id: int) -> Optional[QuestionSelection]:
=======
    def next_question(self, user_id: int) -> Optional[Question]:
>>>>>>> theirs
=======
    def next_question(self, user_id: int) -> Optional[Question]:
>>>>>>> theirs
=======
    def next_question(self, user_id: int) -> Optional[Question]:
>>>>>>> theirs
=======
    def next_question(self, user_id: int) -> Optional[Question]:
>>>>>>> theirs
=======
    def next_question(self, user_id: int) -> Optional[Question]:
>>>>>>> theirs
        bank = get_all_questions()
        if not bank:
            return None

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        candidate_pool = bank
        user_stats = self.storage.user_stats(user_id)
        policy_variant = self.storage.get_policy_variant(user_id)
        selection = select_next_question(
            candidate_pool,
            history=self.storage.answer_history(user_id),
            question_summary=self.storage.question_attempt_summary(user_id),
            total_answers=int(user_stats.get("total_answers", 0)),
            accuracy=float(user_stats.get("accuracy", 0.0)),
            policy_variant=policy_variant,
        )
        if selection:
            return selection

=======
        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
>>>>>>> theirs
=======
        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
>>>>>>> theirs
=======
        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
>>>>>>> theirs
=======
        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
>>>>>>> theirs
=======
        candidate_pool = self._adaptive_candidates(user_id, bank)
        user_stats = self.storage.user_stats(user_id)
>>>>>>> theirs
        weak = user_stats.get("weak_chapters", [])
        weak_chapter = weak[0]["chapter_id"] if weak and weak[0].get("wrongs", 0) > 0 else None
        if weak_chapter:
            weak_candidates = [q for q in candidate_pool if q.chapter_id == weak_chapter]
            if weak_candidates:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
                q = random.choice(weak_candidates)
                return QuestionSelection(question=q, learning={"strategy": "legacy_weak_chapter", "reason": "weak_chapter"})
=======
                return random.choice(weak_candidates)
>>>>>>> theirs
=======
                return random.choice(weak_candidates)
>>>>>>> theirs
=======
                return random.choice(weak_candidates)
>>>>>>> theirs
=======
                return random.choice(weak_candidates)
>>>>>>> theirs
=======
                return random.choice(weak_candidates)
>>>>>>> theirs

        chapter_ids = sorted({q.chapter_id for q in candidate_pool})
        chosen_chapter = self.meta.choose_next_chapter(chapter_ids)
        if chosen_chapter:
            candidates = [q for q in candidate_pool if q.chapter_id == chosen_chapter]
            if candidates:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
                q = random.choice(candidates)
                return QuestionSelection(question=q, learning={"strategy": "legacy_chapter_balance", "reason": "balanced_practice"})

        q = random.choice(candidate_pool)
        return QuestionSelection(question=q, learning={"strategy": "legacy_random", "reason": "balanced_practice"})

    def answer(self, user_id: int, question_id: str, selected_index: int, elapsed_ms: Optional[int] = None) -> Dict[str, Any]:
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
                return random.choice(candidates)

        return random.choice(candidate_pool)

    def answer(self, user_id: int, question_id: str, selected_index: int) -> Dict[str, Any]:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        if selected_index not in {0, 1, 2, 3}:
            raise InvalidAnswerIndexError("selected_index must be 0..3")

        q = get_question_by_id(question_id)
        if q is None:
            raise QuestionNotFoundError("question_id not found")

        correct = q.is_correct(selected_index)
        self.meta.record_usage(q.chapter_id, "offline")
        self.meta.save()
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        self.storage.record_answer(user_id, q.id, q.chapter_id, selected_index, correct, elapsed_ms)
        self.audit(
            "quiz.answer",
            user_id=user_id,
            detail={"question_id": q.id, "correct": correct, "elapsed_ms": elapsed_ms},
        )
        schedule = update_schedule(
            self.storage.get_learning_item(user_id, q.id),
            correct=correct,
            elapsed_ms=elapsed_ms,
            difficulty=q.difficulty,
        )
        self.storage.upsert_learning_item(
            user_id,
            q.id,
            q.chapter_id,
            easiness=schedule.easiness,
            interval_hours=schedule.interval_hours,
            due_at=schedule.due_at,
            repetitions=schedule.repetitions,
            lapses=schedule.lapses,
            last_grade=schedule.grade,
        )
        updated_stats = self.storage.user_stats(user_id)

        return {
            "correct": correct,
            "selected_index": selected_index,
            "correct_index": q.correct_index,
            "correct_choice": q.choices[q.correct_index],
            "explanation": q.explanation,
            "learning": {
                "schedule": {
                    "due_at": schedule.due_at,
                    "interval_hours": schedule.interval_hours,
                    "grade": schedule.grade,
                    "retention": schedule.retention,
                    "easiness": schedule.easiness,
                },
                "current_streak": updated_stats.get("current_streak", 0),
                "accuracy": updated_stats.get("accuracy", 0.0),
            },
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        self.storage.record_answer(user_id, q.id, q.chapter_id, selected_index, correct)

        return {
            "correct": correct,
            "correct_index": q.correct_index,
            "explanation": q.explanation,
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        }

    def stats(self, user_id: int) -> Dict[str, Any]:
        usage = self.meta.meta.get("usage", {})
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        history = self.storage.answer_history(user_id)
        bank = get_all_questions()
        lookup = {q.id: q for q in bank}
        learning = summarize_learning(
            history,
            question_lookup=lookup,
            learning_items=self.storage.learning_items(user_id),
        )
        active_policy = self.storage.get_policy_variant(user_id)
        learning["mastery_model"] = learning.pop("policy", "adaptive_mastery_v2")
        learning["selection_policy"] = active_policy
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        return {
            "global": {
                "total_questions": int(usage.get("total_questions", 0)),
                "online_questions": int(usage.get("online_questions", 0)),
                "offline_questions": int(usage.get("offline_questions", 0)),
            },
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            "user": {
                **self.storage.user_stats(user_id),
                "learning": learning,
            },
        }

    def learning_plan(self, user_id: int) -> Dict[str, Any]:
        bank = get_all_questions()
        lookup = {q.id: q for q in bank}
        history = self.storage.answer_history(user_id)
        learning = summarize_learning(
            history,
            question_lookup=lookup,
            learning_items=self.storage.learning_items(user_id),
        )
        active_policy = self.storage.get_policy_variant(user_id)
        learning["mastery_model"] = learning.pop("policy", "adaptive_mastery_v2")
        learning["selection_policy"] = active_policy
        return learning

    def export_account(self, user_id: int) -> Dict[str, Any]:
        bundle = self.storage.export_user_data(user_id)
        self.audit("account.export", user_id=user_id, detail={"answers": len(bundle.get("answers", []))})
        return bundle

    def import_account(self, user_id: int, bundle: Dict[str, Any]) -> Dict[str, int]:
        result = self.storage.import_user_data(user_id, bundle)
        self.audit("account.import", user_id=user_id, detail=result)
        return result

    def audit(self, event_type: str, *, user_id: Optional[int] = None, detail: Optional[Dict[str, Any]] = None) -> None:
        self.storage.record_audit_event(event_type, user_id=user_id, detail=detail or {})

    def audit_log(self, user_id: int, limit: int = 100) -> Dict[str, Any]:
        return {"events": self.storage.audit_events(user_id=user_id, limit=limit)}

    def record_request(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        route_family: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        self.storage.record_request_metric(
            request_id=request_id,
            method=method,
            path=path,
            route_family=route_family,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        structured_log(
            "http.request",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
        )

    def operations_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        bank = get_all_questions()
        return {
            "service": {
                "api_version": "v1",
                "deployment_profile": current_profile_name(),
                "profile": load_deployment_profile(),
                "viewer": self._learner_id(user_id) if user_id else "system",
            },
            "observability": self.storage.metrics_summary(),
            "content_quality": {
                "question_count": len(bank),
                "chapter_count": len({q.chapter_id for q in bank}),
                "difficulty_counts": {
                    label: len([q for q in bank if q.difficulty == label])
                    for label in ["basic", "standard", "advanced"]
                },
            },
            "experiments": experiment_summary(),
        }

    def get_policy(self, user_id: int) -> Dict[str, Any]:
        return {
            "policy_variant": self.storage.get_policy_variant(user_id),
            "experiment": experiment_summary(),
        }

    def set_policy(self, user_id: int, policy_variant: str) -> Dict[str, Any]:
        normalized = self.storage.set_policy_variant(user_id, policy_variant)
        self.audit("learning.policy.updated", user_id=user_id, detail={"policy_variant": normalized})
        return {"policy_variant": normalized, "experiment": experiment_summary()}
=======
            "user": self.storage.user_stats(user_id),
        }
>>>>>>> theirs
=======
            "user": self.storage.user_stats(user_id),
        }
>>>>>>> theirs
=======
            "user": self.storage.user_stats(user_id),
        }
>>>>>>> theirs
=======
            "user": self.storage.user_stats(user_id),
        }
>>>>>>> theirs
=======
            "user": self.storage.user_stats(user_id),
        }
>>>>>>> theirs
