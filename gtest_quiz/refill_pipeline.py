"""Refill pipeline orchestrating generation, validation, de-duplication, and quota guard."""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import google.generativeai as genai

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank
from gtest_quiz.question_quality import (
    build_duplicate_index,
    is_probable_duplicate,
    validate_generated_question,
)


class RefillConfig:
    def __init__(
        self,
        *,
        model_name: str = "gemini-2.5-flash-lite",
        target_daily: int = 80,
        max_retry: int = 3,
        min_explanation_length: int = 60,
        sleep_seconds_on_429: float = 2.0,
        hard_stop_on_near_quota: bool = True,
    ) -> None:
        self.model_name = model_name
        self.target_daily = target_daily
        self.max_retry = max_retry
        self.min_explanation_length = min_explanation_length
        self.sleep_seconds_on_429 = sleep_seconds_on_429
        self.hard_stop_on_near_quota = hard_stop_on_near_quota


class RefillStats:
    def __init__(self) -> None:
        self.generated = 0
        self.accepted = 0
        self.rejected = 0
        self.duplicates = 0
        self.errors = 0


PROMPT_TEMPLATE = """
あなたはG検定（JDLA）の専門問題作成AIです。

制約:
- 4択問題
- 正解は1つのみ
- 誤答はもっともらしく、知識が曖昧な受験者が誤る内容にする
- 暗記ではなく理解を問う

出力は必ずJSONのみ（コードブロック禁止）:
{
  "question": "",
  "choices": ["","","",""],
  "correct_index": 0,
  "explanation": "",
  "difficulty": "basic|standard|advanced"
}

分野: {group}
項目: {label}
"""


def _build_prompt(group: str, label: str) -> str:
    return PROMPT_TEMPLATE.format(group=group, label=label)


def _safe_parse_json(text: str) -> Optional[Dict[str, object]]:
    try:
        return json.loads(text)
    except Exception:
        # try to trim to JSON block
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


def _generate_once(model: genai.GenerativeModel, prompt: str) -> Optional[Dict[str, object]]:
    try:
        res = model.generate_content(prompt)
        return _safe_parse_json(getattr(res, "text", ""))
    except Exception:
        return None


def _generate_with_retry(model: genai.GenerativeModel, prompt: str, max_retry: int) -> Optional[Dict[str, object]]:
    for _ in range(max_retry):
        data = _generate_once(model, prompt)
        if isinstance(data, dict):
            return data
    return None


def _load_duplicate_index() -> object:
    bank = load_question_bank()
    items = [q.to_dict() for q in bank.values()]
    return build_duplicate_index(items)


def run_refill(config: RefillConfig, meta_path: str = "bank/meta.json") -> RefillStats:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=api_key)

    meta = MetaManager(meta_path)
    meta.load()

    # quota guard (best-effort)
    quota = meta.quota
    if config.hard_stop_on_near_quota and quota.is_near_limit(0.9):
        return RefillStats()

    model = genai.GenerativeModel(config.model_name)

    duplicate_index = _load_duplicate_index()

    chapters = meta.get_all_chapter_labels()
    random.shuffle(chapters)

    stats = RefillStats()
    results: List[Question] = []

    for ch in chapters:
        if stats.accepted >= config.target_daily:
            break

        prompt = _build_prompt("G検定", ch)
        data = _generate_with_retry(model, prompt, config.max_retry)
        stats.generated += 1

        if not data:
            stats.errors += 1
            continue

        validation = validate_generated_question(data, min_explanation_length=config.min_explanation_length)
        if not validation.is_valid:
            stats.rejected += 1
            continue

        if is_probable_duplicate(str(data.get("question", "")), duplicate_index):
            stats.duplicates += 1
            continue

        q = Question(
            id=f"AUTO_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            source="auto_refill_quality",
            created_at=datetime.now(timezone.utc).isoformat(),
            domain="JDLA",
            chapter_group="G検定",
            chapter_id=ch,
            difficulty=str(data.get("difficulty", "standard")),
            question=str(data.get("question", "")),
            choices=[str(x) for x in data.get("choices", [])],
            correct_index=int(data.get("correct_index", 0)),
            explanation=str(data.get("explanation", "")),
            syllabus="G2024",
        )

        results.append(q)
        stats.accepted += 1

        # update duplicate index incrementally
        duplicate_index = build_duplicate_index([*({"question": q.question} for q in results)])

    if results:
        with open("bank/question_bank.jsonl", "a", encoding="utf-8") as f:
            for q in results:
                f.write(json.dumps(q.to_dict(), ensure_ascii=False) + "\n")

        meta.save()

    return stats
