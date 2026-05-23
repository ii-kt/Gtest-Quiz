from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from backend.app.experiments import ADAPTIVE_POLICY, normalize_policy_variant
from backend.app.security import isoformat, token_hash as secure_token_hash, utcnow
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Storage:
    db_path: str = ".runtime/quiz.db"

    def __post_init__(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _token_hash(self, token: str) -> str:
        return secure_token_hash(token)

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_key TEXT UNIQUE NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    token_hash TEXT UNIQUE,
                    display_name TEXT,
                    auth_provider TEXT DEFAULT 'session',
                    policy_variant TEXT DEFAULT 'adaptive_mastery_v2',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    selected_index INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    elapsed_ms INTEGER,
                    answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS learning_items (
                    user_id INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    chapter_id TEXT NOT NULL,
                    easiness REAL NOT NULL DEFAULT 2.3,
                    interval_hours REAL NOT NULL DEFAULT 0,
                    due_at TEXT,
                    repetitions INTEGER NOT NULL DEFAULT 0,
                    lapses INTEGER NOT NULL DEFAULT 0,
                    last_grade INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(user_id, question_id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    request_id TEXT,
                    detail_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    route_family TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user_question ON answers(user_id, question_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user_chapter ON answers(user_id, chapter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_learning_user_due ON learning_items(user_id, due_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_request_metrics_created ON request_metrics(created_at)")
            self._ensure_column(conn, "users", "account_key", "TEXT")
            self._ensure_column(conn, "users", "token_hash", "TEXT")
            self._ensure_column(conn, "users", "display_name", "TEXT")
            self._ensure_column(conn, "users", "auth_provider", "TEXT DEFAULT 'session'")
            self._ensure_column(conn, "users", "policy_variant", "TEXT DEFAULT 'adaptive_mastery_v2'")
            self._ensure_column(conn, "answers", "elapsed_ms", "INTEGER")
            user_columns = self._columns(conn, "users")
            if "username" in user_columns:
                conn.execute(
                    """
                    UPDATE users
                    SET account_key=username
                    WHERE (account_key IS NULL OR account_key='') AND username IS NOT NULL
                    """
                )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_account_key ON users(account_key) WHERE account_key IS NOT NULL"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_token_hash ON users(token_hash) WHERE token_hash IS NOT NULL"
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES(?)",
                ("20260521_phase4_productization",),
            )

    def _columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        return {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        columns = self._columns(conn, table)
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def create_user(
        self,
        account_key: str,
        token: str,
        *,
        display_name: str = "",
        session_expires_at: str = "",
        policy_variant: str = ADAPTIVE_POLICY,
    ) -> Dict[str, Any]:
        token_hash = self._token_hash(token)
        issued_at = isoformat(utcnow())
        expires_at = session_expires_at or isoformat(utcnow())
        policy_variant = normalize_policy_variant(policy_variant)
        with self._connection() as conn:
            user_columns = self._columns(conn, "users")
            insert_columns = ["account_key", "token", "token_hash", "display_name", "auth_provider", "policy_variant"]
            insert_values: List[Any] = [
                account_key,
                f"sha256:{token_hash}",
                token_hash,
                display_name,
                "session",
                policy_variant,
            ]
            if "username" in user_columns:
                insert_columns.insert(1, "username")
                insert_values.insert(1, account_key)
            if "password_hash" in user_columns:
                token_column_index = insert_columns.index("token")
                insert_columns.insert(token_column_index, "password_hash")
                insert_values.insert(token_column_index, f"session:{token_hash[:16]}")
            placeholders = ", ".join("?" for _ in insert_columns)
            conn.execute(
                f"INSERT INTO users({', '.join(insert_columns)}) VALUES({placeholders})",
                tuple(insert_values),
            )
            row = conn.execute(
                "SELECT id, account_key, display_name, token, policy_variant FROM users WHERE account_key=?",
                (account_key,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO sessions(user_id, token_hash, issued_at, expires_at)
                VALUES(?, ?, ?, ?)
                """,
                (int(row["id"]), token_hash, issued_at, expires_at),
            )
            data = dict(row)
            data["token"] = token
            data["session_expires_at"] = expires_at
            return data

    def get_user_by_account_key(self, account_key: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, account_key, display_name, token, policy_variant
                FROM users
                WHERE account_key=?
                """,
                (account_key,),
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT id, account_key, display_name, policy_variant, created_at
                FROM users
                WHERE id=?
                """,
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def rotate_token(self, user_id: int, token: str, *, session_expires_at: str = "") -> Dict[str, Any]:
        token_hash = self._token_hash(token)
        issued_at = isoformat(utcnow())
        expires_at = session_expires_at or isoformat(utcnow())
        with self._connection() as conn:
            conn.execute(
                "UPDATE sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
                (issued_at, user_id),
            )
            conn.execute("UPDATE users SET token=?, token_hash=? WHERE id=?", (f"sha256:{token_hash}", token_hash, user_id))
            conn.execute(
                """
                INSERT INTO sessions(user_id, token_hash, issued_at, expires_at)
                VALUES(?, ?, ?, ?)
                """,
                (user_id, token_hash, issued_at, expires_at),
            )
            row = conn.execute(
                "SELECT id, account_key, display_name, token, policy_variant FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            data = dict(row)
            data["token"] = token
            data["session_expires_at"] = expires_at
            return data

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        token_hash = self._token_hash(token)
        now = isoformat(utcnow())
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.account_key, u.display_name, u.token, u.policy_variant, s.expires_at AS session_expires_at
                FROM sessions s
                INNER JOIN users u ON u.id = s.user_id
                WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>?
                ORDER BY s.id DESC
                LIMIT 1
                """,
                (token_hash, now),
            ).fetchone()
            if row:
                return dict(row)
            session_seen = conn.execute(
                "SELECT 1 FROM sessions WHERE token_hash=? LIMIT 1",
                (token_hash,),
            ).fetchone()
            if session_seen:
                return None
            legacy = conn.execute(
                """
                SELECT id, account_key, display_name, token, policy_variant, '' AS session_expires_at
                FROM users
                WHERE token_hash=? OR token=?
                """,
                (token_hash, token),
            ).fetchone()
            return dict(legacy) if legacy else None

    def revoke_session(self, token: str) -> bool:
        token_hash = self._token_hash(token)
        with self._connection() as conn:
            cur = conn.execute(
                "UPDATE sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (isoformat(utcnow()), token_hash),
            )
            return cur.rowcount > 0

    def expire_session_for_test(self, token: str) -> None:
        token_hash = self._token_hash(token)
        with self._connection() as conn:
            conn.execute(
                "UPDATE sessions SET expires_at=? WHERE token_hash=?",
                ("2000-01-01T00:00:00Z", token_hash),
            )

    def record_answer(
        self,
        user_id: int,
        question_id: str,
        chapter_id: str,
        selected_index: int,
        correct: bool,
        elapsed_ms: Optional[int] = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO answers(user_id, question_id, chapter_id, selected_index, correct, elapsed_ms)
                VALUES(?,?,?,?,?,?)
                """,
                (user_id, question_id, chapter_id, selected_index, 1 if correct else 0, elapsed_ms),
            )

    def answered_question_ids(self, user_id: int) -> List[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT DISTINCT question_id FROM answers WHERE user_id=?", (user_id,)).fetchall()
            return [str(r[0]) for r in rows]

    def answer_history(self, user_id: int, limit: int = 2000) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT question_id, chapter_id, selected_index, correct, elapsed_ms, answered_at
                FROM answers
                WHERE user_id=?
                ORDER BY answered_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def question_attempt_summary(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT question_id,
                       COUNT(*) AS attempts,
                       SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) AS wrongs,
                       MAX(answered_at) AS last_answered_at,
                       AVG(CASE WHEN elapsed_ms IS NULL THEN NULL ELSE elapsed_ms END) AS avg_elapsed_ms
                FROM answers
                WHERE user_id=?
                GROUP BY question_id
                """,
                (user_id,),
            ).fetchall()

            latest_rows = conn.execute(
                """
                SELECT a.question_id, a.correct
                FROM answers a
                INNER JOIN (
                    SELECT question_id, MAX(id) AS max_id
                    FROM answers
                    WHERE user_id=?
                    GROUP BY question_id
                ) latest ON latest.max_id = a.id
                """,
                (user_id,),
            ).fetchall()

            learning_rows = conn.execute(
                """
                SELECT question_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade
                FROM learning_items
                WHERE user_id=?
                """,
                (user_id,),
            ).fetchall()

        latest = {str(r["question_id"]): bool(r["correct"]) for r in latest_rows}
        summary = {
            str(r["question_id"]): {
                "attempts": int(r["attempts"]),
                "wrongs": int(r["wrongs"] or 0),
                "last_answered_at": str(r["last_answered_at"] or ""),
                "last_correct": latest.get(str(r["question_id"]), False),
                "avg_elapsed_ms": float(r["avg_elapsed_ms"] or 0.0),
            }
            for r in rows
        }
        for row in learning_rows:
            qid = str(row["question_id"])
            summary.setdefault(qid, {"attempts": 0, "wrongs": 0, "last_answered_at": "", "last_correct": False})
            summary[qid].update(
                {
                    "easiness": float(row["easiness"]),
                    "interval_hours": float(row["interval_hours"]),
                    "due_at": str(row["due_at"] or ""),
                    "repetitions": int(row["repetitions"]),
                    "lapses": int(row["lapses"]),
                    "last_grade": int(row["last_grade"]),
                }
            )
        return summary

    def get_learning_item(self, user_id: int, question_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT user_id, question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade
                FROM learning_items
                WHERE user_id=? AND question_id=?
                """,
                (user_id, question_id),
            ).fetchone()
            return dict(row) if row else None

    def upsert_learning_item(
        self,
        user_id: int,
        question_id: str,
        chapter_id: str,
        *,
        easiness: float,
        interval_hours: float,
        due_at: str,
        repetitions: int,
        lapses: int,
        last_grade: int,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO learning_items(
                    user_id, question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade, updated_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, question_id) DO UPDATE SET
                    chapter_id=excluded.chapter_id,
                    easiness=excluded.easiness,
                    interval_hours=excluded.interval_hours,
                    due_at=excluded.due_at,
                    repetitions=excluded.repetitions,
                    lapses=excluded.lapses,
                    last_grade=excluded.last_grade,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade),
            )

    def learning_items(self, user_id: int) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade, updated_at
                FROM learning_items
                WHERE user_id=?
                ORDER BY due_at ASC
                """,
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_policy_variant(self, user_id: int) -> str:
        with self._connection() as conn:
            row = conn.execute("SELECT policy_variant FROM users WHERE id=?", (user_id,)).fetchone()
            return normalize_policy_variant(str(row["policy_variant"] if row else ""))

    def set_policy_variant(self, user_id: int, policy_variant: str) -> str:
        normalized = normalize_policy_variant(policy_variant)
        with self._connection() as conn:
            conn.execute("UPDATE users SET policy_variant=? WHERE id=?", (normalized, user_id))
        return normalized

    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        with self._connection() as conn:
            user = conn.execute(
                "SELECT id, account_key, display_name, policy_variant, created_at FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
            answers = conn.execute(
                """
                SELECT question_id, chapter_id, selected_index, correct, elapsed_ms, answered_at
                FROM answers
                WHERE user_id=?
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
            learning = conn.execute(
                """
                SELECT question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade, updated_at
                FROM learning_items
                WHERE user_id=?
                ORDER BY question_id ASC
                """,
                (user_id,),
            ).fetchall()
        return {
            "schema_version": "gtest_quiz_export_v1",
            "exported_at": isoformat(utcnow()),
            "user": dict(user) if user else {"id": user_id},
            "answers": [dict(row) for row in answers],
            "learning_items": [dict(row) for row in learning],
        }

    def import_user_data(self, user_id: int, bundle: Dict[str, Any]) -> Dict[str, int]:
        answers = bundle.get("answers", [])
        learning_items = bundle.get("learning_items", [])
        if not isinstance(answers, list):
            answers = []
        if not isinstance(learning_items, list):
            learning_items = []

        from gtest_quiz.question_bank import get_question_by_id

        imported_answers = 0
        imported_learning = 0
        with self._connection() as conn:
            for row in answers[:5000]:
                if not isinstance(row, dict):
                    continue
                qid = str(row.get("question_id", ""))[:128]
                question = get_question_by_id(qid)
                if question is None:
                    continue
                try:
                    selected_index = int(row.get("selected_index", 0))
                except (TypeError, ValueError):
                    selected_index = 0
                selected_index = max(0, min(3, selected_index))
                correct = question.is_correct(selected_index)
                try:
                    elapsed_ms = int(row.get("elapsed_ms", 0) or 0)
                except (TypeError, ValueError):
                    elapsed_ms = 0
                conn.execute(
                    """
                    INSERT INTO answers(user_id, question_id, chapter_id, selected_index, correct, elapsed_ms, answered_at)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        user_id,
                        question.id,
                        question.chapter_id,
                        selected_index,
                        1 if correct else 0,
                        max(0, min(3_600_000, elapsed_ms)),
                        str(row.get("answered_at") or isoformat(utcnow())),
                    ),
                )
                imported_answers += 1
            for row in learning_items[:5000]:
                if not isinstance(row, dict):
                    continue
                qid = str(row.get("question_id", ""))[:128]
                question = get_question_by_id(qid)
                if question is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO learning_items(
                        user_id, question_id, chapter_id, easiness, interval_hours, due_at, repetitions, lapses, last_grade, updated_at
                    )
                    VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, question_id) DO UPDATE SET
                        chapter_id=excluded.chapter_id,
                        easiness=excluded.easiness,
                        interval_hours=excluded.interval_hours,
                        due_at=excluded.due_at,
                        repetitions=excluded.repetitions,
                        lapses=excluded.lapses,
                        last_grade=excluded.last_grade,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        user_id,
                        question.id,
                        question.chapter_id,
                        float(row.get("easiness", 2.3) or 2.3),
                        float(row.get("interval_hours", 0.0) or 0.0),
                        str(row.get("due_at") or ""),
                        int(row.get("repetitions", 0) or 0),
                        int(row.get("lapses", 0) or 0),
                        int(row.get("last_grade", 0) or 0),
                    ),
                )
                imported_learning += 1
        return {"imported_answers": imported_answers, "imported_learning_items": imported_learning}

    def record_audit_event(
        self,
        event_type: str,
        *,
        user_id: Optional[int] = None,
        request_id: str = "",
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO audit_events(user_id, event_type, request_id, detail_json) VALUES(?,?,?,?)",
                (user_id, event_type, request_id, json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)),
            )

    def audit_events(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            if user_id is None:
                rows = conn.execute(
                    """
                    SELECT id, user_id, event_type, request_id, detail_json, created_at
                    FROM audit_events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, user_id, event_type, request_id, detail_json, created_at
                    FROM audit_events
                    WHERE user_id=?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            try:
                item["detail"] = json.loads(str(item.pop("detail_json") or "{}"))
            except json.JSONDecodeError:
                item["detail"] = {}
            events.append(item)
        return events

    def record_request_metric(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        route_family: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO request_metrics(request_id, method, path, route_family, status_code, latency_ms)
                VALUES(?,?,?,?,?,?)
                """,
                (request_id, method, path, route_family, status_code, latency_ms),
            )

    def metrics_summary(self) -> Dict[str, Any]:
        with self._connection() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM request_metrics").fetchone()["c"]
            latency = conn.execute(
                "SELECT AVG(latency_ms) AS avg_latency, MAX(latency_ms) AS max_latency FROM request_metrics"
            ).fetchone()
            statuses = conn.execute(
                """
                SELECT status_code, COUNT(*) AS c
                FROM request_metrics
                GROUP BY status_code
                ORDER BY status_code ASC
                """
            ).fetchall()
            routes = conn.execute(
                """
                SELECT route_family, COUNT(*) AS c, AVG(latency_ms) AS avg_latency
                FROM request_metrics
                GROUP BY route_family
                ORDER BY c DESC, route_family ASC
                LIMIT 12
                """
            ).fetchall()
        return {
            "requests": {
                "total": int(total),
                "avg_latency_ms": round(float(latency["avg_latency"] or 0.0), 2),
                "max_latency_ms": round(float(latency["max_latency"] or 0.0), 2),
                "status_counts": {str(row["status_code"]): int(row["c"]) for row in statuses},
                "routes": [
                    {
                        "route_family": row["route_family"],
                        "count": int(row["c"]),
                        "avg_latency_ms": round(float(row["avg_latency"] or 0.0), 2),
                    }
                    for row in routes
                ],
            },
            "audit_events": len(self.audit_events(limit=1000)),
        }

    def migration_status(self) -> Dict[str, Any]:
        with self._connection() as conn:
            rows = conn.execute("SELECT version, applied_at FROM schema_migrations ORDER BY version ASC").fetchall()
        return {"db_path": self.db_path, "migrations": [dict(row) for row in rows]}

    def user_stats(self, user_id: int) -> Dict[str, Any]:
        with self._connection() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM answers WHERE user_id=?", (user_id,)).fetchone()["c"]
            correct = conn.execute("SELECT COUNT(*) c FROM answers WHERE user_id=? AND correct=1", (user_id,)).fetchone()["c"]
            recent = conn.execute(
                """
                SELECT correct
                FROM answers
                WHERE user_id=?
                ORDER BY answered_at DESC, id DESC
                LIMIT 200
                """,
                (user_id,),
            ).fetchall()
            weak = conn.execute(
                """
                SELECT chapter_id,
                       SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) AS wrongs,
                       COUNT(*) AS total
                FROM answers
                WHERE user_id=?
                GROUP BY chapter_id
                ORDER BY wrongs DESC, total DESC
                LIMIT 5
                """,
                (user_id,),
            ).fetchall()
            streak = 0
            for row in recent:
                if int(row["correct"]) == 1:
                    streak += 1
                else:
                    break
            return {
                "total_answers": int(total),
                "correct_answers": int(correct),
                "accuracy": (float(correct) / float(total)) if total else 0.0,
                "current_streak": streak,
                "weak_chapters": [dict(r) for r in weak],
            }
