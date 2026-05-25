from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.question_quality import build_duplicate_index, is_probable_duplicate, validate_generated_question


BANK_PATH = Path("bank/question_bank.jsonl")
REQUIRED_METADATA = ("source", "created_at", "domain", "chapter_group")
MIN_EXPLANATION_LENGTH = 80


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise AssertionError(f"{path}:{line_no}: invalid JSON: {e}") from e
            if not isinstance(data, dict):
                raise AssertionError(f"{path}:{line_no}: JSONL row must be an object")
            data["_line_no"] = line_no
            yield data


def validate_question_bank(path: Path = BANK_PATH) -> List[str]:
    if not path.exists():
        return [f"missing question bank: {path}"]

    errors: List[str] = []
    rows = list(_iter_jsonl(path))
    ids = Counter(str(row.get("id", "")) for row in rows)
    seen_questions: List[Dict[str, Any]] = []
    duplicate_index = build_duplicate_index(seen_questions)

    for row in rows:
        line_no = row.get("_line_no", "?")
        qid = str(row.get("id", ""))
        if not qid:
            errors.append(f"{path}:{line_no}: missing id")
        elif ids[qid] > 1:
            errors.append(f"{path}:{line_no}: duplicate id {qid}")

        choices = row.get("choices", [])
        correct_index = row.get("correct_index", -1)
        if not isinstance(choices, list) or len(choices) != 4:
            errors.append(f"{path}:{line_no}: choices must contain exactly four items")
        if correct_index not in {0, 1, 2, 3}:
            errors.append(f"{path}:{line_no}: correct_index must be 0..3")

        for field in REQUIRED_METADATA:
            if not str(row.get(field, "")).strip():
                errors.append(f"{path}:{line_no}: missing metadata field {field}")
        created_at = str(row.get("created_at", "")).strip()
        if created_at:
            try:
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}:{line_no}: created_at must be ISO-8601")

        quality = validate_generated_question(row, min_explanation_length=MIN_EXPLANATION_LENGTH)
        if not quality.is_valid:
            errors.append(f"{path}:{line_no}: quality validation failed: {', '.join(quality.reasons)}")
        elif any(reason == "explanation is too short" for reason in quality.reasons):
            errors.append(f"{path}:{line_no}: explanation must be at least {MIN_EXPLANATION_LENGTH} characters")

        question = str(row.get("question", ""))
        if is_probable_duplicate(question, duplicate_index):
            errors.append(f"{path}:{line_no}: probable duplicate question")
        seen_questions.append(row)
        duplicate_index = build_duplicate_index(seen_questions)

    return errors


def main() -> None:
    errors = validate_question_bank()
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"question bank ok: {BANK_PATH}")


if __name__ == "__main__":
    main()
