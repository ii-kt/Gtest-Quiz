from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Storage:
    db_path: str = "backend/app/quiz.db"

    def __post_init__(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
                    answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user ON answers(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user_question ON answers(user_id, question_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_user_chapter ON answers(user_id, chapter_id)")

    def create_user(self, username: str, token: str) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute("INSERT INTO users(username, token) VALUES(?, ?)", (username, token))
            row = conn.execute("SELECT id, username, token FROM users WHERE username=?", (username,)).fetchone()
            return dict(row)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT id, username, token FROM users WHERE username=?", (username,)).fetchone()
            return dict(row) if row else None

    def rotate_token(self, user_id: int, token: str) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute("UPDATE users SET token=? WHERE id=?", (token, user_id))
            row = conn.execute("SELECT id, username, token FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row)

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT id, username, token FROM users WHERE token=?", (token,)).fetchone()
            return dict(row) if row else None

    def record_answer(self, user_id: int, question_id: str, chapter_id: str, selected_index: int, correct: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO answers(user_id, question_id, chapter_id, selected_index, correct) VALUES(?,?,?,?,?)",
                (user_id, question_id, chapter_id, selected_index, 1 if correct else 0),
            )

    def answered_question_ids(self, user_id: int) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT DISTINCT question_id FROM answers WHERE user_id=?", (user_id,)).fetchall()
            return [str(r[0]) for r in rows]

    def user_stats(self, user_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM answers WHERE user_id=?", (user_id,)).fetchone()["c"]
            correct = conn.execute("SELECT COUNT(*) c FROM answers WHERE user_id=? AND correct=1", (user_id,)).fetchone()["c"]
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
            return {
                "total_answers": int(total),
                "correct_answers": int(correct),
                "accuracy": (float(correct) / float(total)) if total else 0.0,
                "weak_chapters": [dict(r) for r in weak],
            }
