from __future__ import annotations

import json, os, time, random
from datetime import datetime, timezone
from typing import List, Optional, Dict

import google.generativeai as genai

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank
from gtest_quiz.question_quality import (
    build_duplicate_index,
    is_probable_duplicate,
    validate_generated_question,
)
from gtest_quiz.env import get_env, load_dotenv


class Config:
    model = "gemini-2.5-flash-lite"
    target = 80
    retry = 3
    sleep = 2
    min_explain = 80


def _gen(model, prompt):
    try:
        r = model.generate_content(prompt)
        return json.loads(r.text)
    except Exception:
        return None


def _gen_retry(model, prompt):
    for _ in range(Config.retry):
        data = _gen(model, prompt)
        if isinstance(data, dict):
            return data
        time.sleep(Config.sleep)
    return None


def run():
    load_dotenv()
    key = get_env("GEMINI_API_KEY")
    if not key:
        return

    genai.configure(api_key=key)

    meta = MetaManager("bank/meta.json")
    meta.load()

    quota = meta.get_quota_manager()

    bank = load_question_bank()
    dup_index = build_duplicate_index([q.to_dict() for q in bank.values()])

    model = genai.GenerativeModel(Config.model)

    chapters = meta.get_all_chapter_labels()
    random.shuffle(chapters)

    results: List[Question] = []

    for ch in chapters:
        if len(results) >= Config.target:
            break

        if quota.is_near_limit(0.9):
            break

        prompt = f"G検定 問題生成: {ch}"

        data = _gen_retry(model, prompt)
        if not data:
            continue

        v = validate_generated_question(data, Config.min_explain)
        if not v.is_valid:
            continue

        if is_probable_duplicate(data["question"], dup_index):
            continue

        q = Question(
            id=str(datetime.now(timezone.utc).timestamp()),
            source="refill_v2",
            created_at=datetime.now(timezone.utc).isoformat(),
            domain="JDLA",
            chapter_group="G検定",
            chapter_id=ch,
            difficulty=data.get("difficulty","standard"),
            question=data["question"],
            choices=data["choices"],
            correct_index=int(data["correct_index"]),
            explanation=data["explanation"],
            syllabus="G2024",
        )

        results.append(q)

        dup_index = build_duplicate_index([
            *[q.to_dict() for q in bank.values()],
            *[r.to_dict() for r in results]
        ])

        quota.add_usage(2000)

    if results:
        with open("bank/question_bank.jsonl","a",encoding="utf-8") as f:
            for q in results:
                f.write(json.dumps(q.to_dict(),ensure_ascii=False)+"\n")

    meta.save()
