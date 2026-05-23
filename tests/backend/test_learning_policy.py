from datetime import datetime, timedelta, timezone

from backend.app.learning import (
    grade_answer,
    select_next_question,
    update_schedule,
)
from gtest_quiz.models import Question


def _q(qid: str, chapter: str, difficulty: str = "standard") -> Question:
    return Question(
        id=qid,
        source="test",
        created_at="2026-01-01T00:00:00Z",
        domain="技術分野",
        chapter_group="group",
        chapter_id=chapter,
        difficulty=difficulty,
        question=f"{qid} question text long enough",
        choices=["a", "b", "c", "d"],
        correct_index=0,
        explanation="explanation long enough for tests",
        syllabus="G2024_v1.3",
    )


def test_update_schedule_promotes_correct_fast_answer():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    schedule = update_schedule(None, correct=True, elapsed_ms=10_000, difficulty="basic", now=now)
    assert schedule.grade == 5
    assert schedule.repetitions == 1
    assert schedule.interval_hours >= 12
    assert schedule.due_at.startswith("2026-01-01T12")


def test_update_schedule_resets_on_wrong_answer():
    previous = {"easiness": 2.5, "interval_hours": 48, "repetitions": 3, "lapses": 0}
    schedule = update_schedule(previous, correct=False, elapsed_ms=50_000, difficulty="advanced")
    assert schedule.grade < 3
    assert schedule.repetitions == 0
    assert schedule.lapses == 1
    assert schedule.interval_hours <= 2


def test_selector_prioritizes_due_review_over_unseen_when_overdue():
    now = datetime(2026, 1, 3, tzinfo=timezone.utc)
    due_question = _q("due", "chapter-a")
    new_question = _q("new", "chapter-b")
    selection = select_next_question(
        [new_question, due_question],
        history=[
            {
                "question_id": "due",
                "chapter_id": "chapter-a",
                "correct": 1,
                "elapsed_ms": 20_000,
                "answered_at": "2026-01-01T00:00:00Z",
            }
        ],
        question_summary={
            "due": {
                "attempts": 1,
                "wrongs": 0,
                "last_correct": True,
                "last_answered_at": "2026-01-01T00:00:00Z",
                "avg_elapsed_ms": 20_000,
                "due_at": (now - timedelta(hours=96)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        },
        total_answers=12,
        accuracy=0.9,
        now=now,
    )
    assert selection is not None
    assert selection.question.id == "due"
    assert selection.learning["reason"] == "review_due"


def test_grade_answer_uses_response_time():
    assert grade_answer(True, 8_000, "basic") == 5
    assert grade_answer(True, 120_000, "advanced") == 3
    assert grade_answer(False, 8_000, "basic") == 2
