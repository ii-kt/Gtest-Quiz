import sqlite3

import pytest

from backend.app.experiments import ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY
from backend.app.services import QuizService, UnauthorizedError
from gtest_quiz.question_bank import get_question_by_id


def test_session_refresh_revokes_previous_token_and_policy_can_be_changed(tmp_path):
    service = QuizService(db_path=str(tmp_path / "quiz.db"), meta_path=str(tmp_path / "meta.json"))
    created = service.start_session()
    assert created["session_expires_at"]
    assert created["learner_id"].startswith("L")
    assert created["policy_variant"] == ADAPTIVE_POLICY

    user = service.user_from_token(created["token"])
    refreshed = service.refresh_session(int(user["id"]))
    assert refreshed["token"] != created["token"]

    with pytest.raises(UnauthorizedError):
        service.user_from_token(created["token"])

    user = service.user_from_token(refreshed["token"])
    policy = service.set_policy(int(user["id"]), CHAPTER_BALANCED_POLICY)
    assert policy["policy_variant"] == CHAPTER_BALANCED_POLICY
    assert service.get_policy(int(user["id"]))["policy_variant"] == CHAPTER_BALANCED_POLICY

    service.storage.expire_session_for_test(refreshed["token"])
    with pytest.raises(UnauthorizedError):
        service.user_from_token(refreshed["token"])


def test_account_import_recomputes_correctness_audit_and_metrics(tmp_path):
    service = QuizService(db_path=str(tmp_path / "quiz.db"), meta_path=str(tmp_path / "meta.json"))
    created = service.start_session()
    user = service.user_from_token(created["token"])
    selection = service.next_question(int(user["id"]))
    assert selection is not None
    q = selection.question
    wrong_index = next(idx for idx in range(4) if idx != q.correct_index)

    malicious_bundle = {
        "schema_version": "gtest_quiz_export_v1",
        "answers": [
            {
                "question_id": q.id,
                "chapter_id": "forged",
                "selected_index": wrong_index,
                "correct": 1,
                "elapsed_ms": 900,
                "answered_at": "2026-01-01T00:00:00Z",
            }
        ],
        "learning_items": [],
    }
    imported = service.import_account(int(user["id"]), malicious_bundle)
    assert imported["imported_answers"] == 1
    stats = service.storage.user_stats(int(user["id"]))
    assert stats["correct_answers"] == 0

    exported = service.export_account(int(user["id"]))
    assert exported["answers"][0]["chapter_id"] == get_question_by_id(q.id).chapter_id

    service.record_request(
        request_id="test-request",
        method="GET",
        path="/api/v1/health",
        route_family="/api/v1/health",
        status_code=200,
        latency_ms=12.4,
    )
    metrics = service.operations_metrics(int(user["id"]))
    assert metrics["observability"]["requests"]["total"] >= 1
    assert metrics["content_quality"]["question_count"] > 0
    assert service.audit_log(int(user["id"]))["events"]


def test_legacy_account_columns_migrate_to_session_account_key(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "INSERT INTO users(username, password_hash, token) VALUES(?,?,?)",
            ("legacy-learner", "legacy-hash", "legacy-token"),
        )

    service = QuizService(db_path=str(db_path), meta_path=str(tmp_path / "meta.json"))
    created = service.start_session()
    user = service.user_from_token(created["token"])
    assert user["account_key"].startswith("learner_")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        legacy = conn.execute("SELECT account_key FROM users WHERE username=?", ("legacy-learner",)).fetchone()
        created_row = conn.execute(
            "SELECT username, account_key, password_hash FROM users WHERE account_key=?",
            (user["account_key"],),
        ).fetchone()

    assert legacy["account_key"] == "legacy-learner"
    assert created_row["username"] == user["account_key"]
    assert created_row["password_hash"].startswith("session:")
