from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from backend.app.experiments import ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY, RANDOM_POLICY, normalize_policy_variant
from gtest_quiz.models import Question


DIFFICULTY_LEVEL = {
    "basic": 0.25,
    "standard": 0.55,
    "advanced": 0.85,
}

EXPECTED_TIME_MS = {
    "basic": 22_000,
    "standard": 36_000,
    "advanced": 52_000,
}


@dataclass(frozen=True)
class QuestionSelection:
    question: Question
    learning: Dict[str, Any]


@dataclass(frozen=True)
class ScheduleUpdate:
    easiness: float
    interval_hours: float
    due_at: str
    repetitions: int
    lapses: int
    grade: int
    retention: float


@dataclass(frozen=True)
class SelectionWeights:
    review: float = 0.38
    unseen: float = 0.22
    weakness: float = 0.24
    question_gap: float = 0.12
    difficulty_fit: float = 0.08
    jitter: float = 0.015


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00").replace(" ", "T")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def wilson_lower_bound(correct: int, total: int, z: float = 1.28) -> float:
    if total <= 0:
        return 0.0
    p = correct / total
    denom = 1 + (z * z / total)
    centre = p + (z * z / (2 * total))
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return max(0.0, min(1.0, (centre - margin) / denom))


def response_time_score(elapsed_ms: Optional[int], difficulty: str) -> float:
    if not elapsed_ms or elapsed_ms <= 0:
        return 0.55
    expected = EXPECTED_TIME_MS.get(difficulty, EXPECTED_TIME_MS["standard"])
    ratio = max(0.15, min(3.0, elapsed_ms / expected))
    return max(0.0, min(1.0, 1.2 - (ratio * 0.35)))


def grade_answer(correct: bool, elapsed_ms: Optional[int], difficulty: str) -> int:
    if not correct:
        return 2 if response_time_score(elapsed_ms, difficulty) >= 0.8 else 1
    speed = response_time_score(elapsed_ms, difficulty)
    if speed >= 0.82:
        return 5
    if speed >= 0.55:
        return 4
    return 3


def update_schedule(
    previous: Optional[Dict[str, Any]],
    *,
    correct: bool,
    elapsed_ms: Optional[int],
    difficulty: str,
    now: Optional[datetime] = None,
) -> ScheduleUpdate:
    now = now or _now()
    grade = grade_answer(correct, elapsed_ms, difficulty)
    easiness = float((previous or {}).get("easiness", 2.3))
    interval = float((previous or {}).get("interval_hours", 0.0))
    repetitions = int((previous or {}).get("repetitions", 0))
    lapses = int((previous or {}).get("lapses", 0))
    difficulty_penalty = 1.0 + DIFFICULTY_LEVEL.get(difficulty, 0.55) * 0.18

    if grade < 3:
        lapses += 1
        repetitions = 0
        easiness = max(1.3, easiness - 0.22)
        interval = 2.0 if grade == 2 else 0.5
    else:
        repetitions += 1
        speed_bonus = (response_time_score(elapsed_ms, difficulty) - 0.55) * 0.18
        easiness = max(1.3, min(2.85, easiness + (0.08 * (grade - 3)) + speed_bonus))
        if repetitions == 1:
            interval = 12.0
        elif repetitions == 2:
            interval = 48.0
        else:
            interval = max(24.0, interval * easiness / difficulty_penalty)

    retention = retention_probability(now, _iso(now + timedelta(hours=interval)), interval)
    return ScheduleUpdate(
        easiness=easiness,
        interval_hours=round(interval, 2),
        due_at=_iso(now + timedelta(hours=interval)),
        repetitions=repetitions,
        lapses=lapses,
        grade=grade,
        retention=retention,
    )


def retention_probability(now: datetime, due_at: str, interval_hours: float) -> float:
    due = _parse_timestamp(due_at)
    if due is None or interval_hours <= 0:
        return 0.35
    elapsed_since_last = max(0.0, interval_hours - ((due - now).total_seconds() / 3600))
    stability = max(1.0, interval_hours)
    return max(0.0, min(1.0, math.exp(-elapsed_since_last / stability)))


def _review_urgency(summary: Dict[str, Any], now: Optional[datetime] = None) -> float:
    now = now or _now()
    attempts = int(summary.get("attempts", 0))
    if attempts <= 0:
        return 0.35

    due_at = _parse_timestamp(str(summary.get("due_at", "")))
    if due_at is not None:
        delta_hours = (now - due_at).total_seconds() / 3600
        if delta_hours >= 0:
            return min(1.0, 0.65 + (delta_hours / 48))
        return max(0.0, 0.45 + (delta_hours / 48))

    last_at = _parse_timestamp(str(summary.get("last_answered_at", "")))
    if last_at is None:
        return 0.2
    age_hours = max(0.0, (now - last_at).total_seconds() / 3600)
    return max(0.0, min(1.0, age_hours / 24))


def question_mastery(summary: Dict[str, Any], difficulty: str, now: Optional[datetime] = None) -> float:
    attempts = int(summary.get("attempts", 0))
    wrongs = int(summary.get("wrongs", 0))
    correct = max(0, attempts - wrongs)
    difficulty_level = DIFFICULTY_LEVEL.get(difficulty, DIFFICULTY_LEVEL["standard"])
    prior_strength = 3.0
    prior = 0.68 - (difficulty_level * 0.22)
    posterior = (correct + prior * prior_strength) / (attempts + prior_strength) if attempts else 0.0
    conservative = wilson_lower_bound(correct, attempts) if attempts else 0.0
    speed = response_time_score(int(summary.get("avg_elapsed_ms", 0) or 0), difficulty)
    urgency = _review_urgency(summary, now)
    scheduled_penalty = 0.22 * urgency
    mastery = (posterior * 0.52) + (conservative * 0.28) + (speed * 0.20) - scheduled_penalty
    return max(0.0, min(1.0, mastery))


def build_chapter_mastery(
    answer_rows: Iterable[Dict[str, Any]],
    question_lookup: Optional[Dict[str, Question]] = None,
) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in answer_rows:
        chapter_id = str(row.get("chapter_id", ""))
        if not chapter_id:
            continue
        q = (question_lookup or {}).get(str(row.get("question_id", "")))
        difficulty = q.difficulty if q else "standard"
        bucket = grouped.setdefault(
            chapter_id,
            {"total": 0, "correct": 0, "elapsed": [], "difficulty_sum": 0.0},
        )
        bucket["total"] += 1
        bucket["correct"] += 1 if int(row.get("correct", 0)) == 1 else 0
        if row.get("elapsed_ms") is not None:
            bucket["elapsed"].append(int(row.get("elapsed_ms") or 0))
        bucket["difficulty_sum"] += DIFFICULTY_LEVEL.get(difficulty, DIFFICULTY_LEVEL["standard"])

    mastery: Dict[str, Dict[str, Any]] = {}
    for chapter_id, values in grouped.items():
        total = int(values["total"])
        correct = int(values["correct"])
        avg_elapsed = (sum(values["elapsed"]) / len(values["elapsed"])) if values["elapsed"] else 0.0
        difficulty_avg = values["difficulty_sum"] / total if total else DIFFICULTY_LEVEL["standard"]
        accuracy = (correct / total) if total else 0.0
        conservative = wilson_lower_bound(correct, total)
        confidence = min(1.0, total / 12)
        speed = response_time_score(int(avg_elapsed), _difficulty_label(difficulty_avg))
        mastery_score = max(
            0.0,
            min(1.0, (conservative * 0.55) + (accuracy * 0.25 * confidence) + (speed * 0.20)),
        )
        mastery[chapter_id] = {
            "chapter_id": chapter_id,
            "total": total,
            "correct": correct,
            "wrongs": total - correct,
            "accuracy": accuracy,
            "avg_elapsed_ms": avg_elapsed,
            "mastery": mastery_score,
            "priority": 1.0 - mastery_score,
        }
    return mastery


def _target_difficulty(total_answers: int, accuracy: float) -> float:
    if total_answers < 8 or accuracy < 0.58:
        return DIFFICULTY_LEVEL["basic"]
    if accuracy < 0.78:
        return DIFFICULTY_LEVEL["standard"]
    return DIFFICULTY_LEVEL["advanced"]


def _reason_for_score(unseen: bool, weakness: float, review: float) -> str:
    if review >= 0.68 and not unseen:
        return "review_due"
    if weakness >= 0.58 and not unseen:
        return "weak_chapter"
    if unseen:
        return "new"
    return "balanced_practice"


def select_next_question(
    bank: List[Question],
    *,
    history: List[Dict[str, Any]],
    question_summary: Dict[str, Dict[str, Any]],
    total_answers: int,
    accuracy: float,
    policy_variant: str = ADAPTIVE_POLICY,
    weights: SelectionWeights = SelectionWeights(),
    now: Optional[datetime] = None,
) -> Optional[QuestionSelection]:
    if not bank:
        return None

    policy_variant = normalize_policy_variant(policy_variant)
    now = now or _now()
    if policy_variant == RANDOM_POLICY:
        question = random.choice(bank)
        return QuestionSelection(
            question=question,
            learning={
                "strategy": RANDOM_POLICY,
                "reason": "baseline_random",
                "policy_variant": RANDOM_POLICY,
                "explain": {"sample_size": len(bank)},
            },
        )

    if policy_variant == CHAPTER_BALANCED_POLICY:
        attempts_by_chapter: Dict[str, int] = {}
        for row in history:
            chapter = str(row.get("chapter_id", ""))
            if chapter:
                attempts_by_chapter[chapter] = attempts_by_chapter.get(chapter, 0) + 1
        min_attempts = min((attempts_by_chapter.get(q.chapter_id, 0) for q in bank), default=0)
        candidates = [q for q in bank if attempts_by_chapter.get(q.chapter_id, 0) == min_attempts]
        unseen = [q for q in candidates if int(question_summary.get(q.id, {}).get("attempts", 0)) == 0]
        question = random.choice(unseen or candidates or bank)
        return QuestionSelection(
            question=question,
            learning={
                "strategy": CHAPTER_BALANCED_POLICY,
                "reason": "chapter_balance",
                "policy_variant": CHAPTER_BALANCED_POLICY,
                "chapter_attempts": attempts_by_chapter.get(question.chapter_id, 0),
                "explain": {"min_chapter_attempts": min_attempts, "candidate_count": len(candidates)},
            },
        )

    question_lookup = {q.id: q for q in bank}
    chapter_mastery = build_chapter_mastery(history, question_lookup)
    target = _target_difficulty(total_answers, accuracy)
    scored: List[tuple[float, Question, Dict[str, Any]]] = []

    for question in bank:
        summary = question_summary.get(question.id, {})
        attempts = int(summary.get("attempts", 0))
        unseen = attempts == 0
        chapter = chapter_mastery.get(question.chapter_id, {})
        q_mastery = question_mastery(summary, question.difficulty, now) if attempts else 0.0
        weakness = float(chapter.get("priority", 0.72 if unseen else 0.35))
        review = _review_urgency(summary, now)
        difficulty = DIFFICULTY_LEVEL.get(question.difficulty, DIFFICULTY_LEVEL["standard"])
        difficulty_fit = 1.0 - min(1.0, abs(difficulty - target))

        due_bonus = weights.review * review if not unseen else 0.0
        new_bonus = weights.unseen if unseen else 0.0
        score = (
            due_bonus
            + new_bonus
            + (weights.weakness * weakness)
            + (weights.question_gap * (1.0 - q_mastery))
            + (weights.difficulty_fit * difficulty_fit)
            + random.uniform(0, weights.jitter)
        )
        due_at = str(summary.get("due_at", ""))
        learning = {
            "strategy": "adaptive_mastery_v2",
            "reason": _reason_for_score(unseen, weakness, review),
            "policy_variant": ADAPTIVE_POLICY,
            "chapter_mastery": float(chapter.get("mastery", 0.0)),
            "chapter_priority": weakness,
            "question_mastery": q_mastery,
            "review_urgency": review,
            "attempts": attempts,
            "target_difficulty": _difficulty_label(target),
            "due_at": due_at,
            "explain": {
                "due_bonus": round(due_bonus, 4),
                "new_bonus": round(new_bonus, 4),
                "weakness": round(weakness, 4),
                "difficulty_fit": round(difficulty_fit, 4),
                "score": round(score, 4),
            },
        }
        scored.append((score, question, learning))

    scored.sort(key=lambda item: item[0], reverse=True)
    _, question, learning = scored[0]
    return QuestionSelection(question=question, learning=learning)


def _difficulty_label(target: float) -> str:
    return min(DIFFICULTY_LEVEL, key=lambda label: abs(DIFFICULTY_LEVEL[label] - target))


def summarize_learning(
    answer_rows: List[Dict[str, Any]],
    *,
    question_lookup: Optional[Dict[str, Question]] = None,
    learning_items: Optional[List[Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or _now()
    chapters = sorted(
        build_chapter_mastery(answer_rows, question_lookup).values(),
        key=lambda item: (float(item["mastery"]), -int(item["total"])),
    )
    items = learning_items or []
    due_now = [item for item in items if (_parse_timestamp(str(item.get("due_at", ""))) or now) <= now]
    next_due = sorted(
        [item for item in items if item.get("due_at")],
        key=lambda item: str(item.get("due_at", "")),
    )[:8]
    return {
        "policy": "adaptive_mastery_v2",
        "chapters": chapters,
        "weakest": chapters[:5],
        "schedule": {
            "tracked_items": len(items),
            "due_now": len(due_now),
            "next_due": next_due,
        },
    }
