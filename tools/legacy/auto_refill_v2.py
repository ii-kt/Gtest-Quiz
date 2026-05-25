# AUTO-REFILL V2: HIGH QUALITY PIPELINE

from __future__ import annotations
import json, os, random, hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import google.generativeai as genai

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank

# ===== CONFIG =====
TARGET_DAILY_GENERATION = 80
MAX_RETRY = 3
MODEL_NAME = "gemini-3.5-flash"

# ===== UTILS =====

def hash_question(q: str) -> str:
    return hashlib.md5(q.strip().encode()).hexdigest()


def load_existing_hashes() -> set:
    bank = load_question_bank()
    return {hash_question(q.question) for q in bank.values()}


def build_prompt(group: str, label: str) -> str:
    return f"""
あなたはG検定の専門問題作成AI。

要求:
- 4択問題
- 誤答も妥当で紛らわしい
- 実務的理解を問う

出力(JSONのみ):
{{
"question": "",
"choices": ["","","",""],
"correct_index": 0,
"explanation": "",
"difficulty": "basic|standard|advanced"
}}

分野:{group}
項目:{label}
"""


def validate(q: dict) -> bool:
    if not q.get("question"):
        return False
    if len(q.get("choices", [])) != 4:
        return False
    if not (0 <= int(q.get("correct_index", -1)) <= 3):
        return False
    if len(q.get("explanation", "")) < 20:
        return False
    return True


def generate(model, prompt: str) -> Optional[dict]:
    for _ in range(MAX_RETRY):
        try:
            res = model.generate_content(prompt)
            data = json.loads(res.text)
            if validate(data):
                return data
        except Exception:
            continue
    return None


def main():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return
    genai.configure(api_key=key)

    meta = MetaManager("bank/meta.json")
    meta.load()

    model = genai.GenerativeModel(MODEL_NAME)

    existing_hashes = load_existing_hashes()

    chapters = meta.get_all_chapter_labels()
    random.shuffle(chapters)

    results: List[Question] = []

    for ch in chapters:
        if len(results) >= TARGET_DAILY_GENERATION:
            break

        prompt = build_prompt("G検定", ch)
        data = generate(model, prompt)
        if not data:
            continue

        h = hash_question(data["question"])
        if h in existing_hashes:
            continue

        q = Question(
            id=f"AUTO_{datetime.now(timezone.utc).timestamp()}",
            source="auto_refill_v2",
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
        existing_hashes.add(h)

    if not results:
        return

    with open("bank/question_bank.jsonl", "a", encoding="utf-8") as f:
        for q in results:
            f.write(json.dumps(q.to_dict(), ensure_ascii=False) + "\n")

    meta.save()


if __name__ == "__main__":
    main()
