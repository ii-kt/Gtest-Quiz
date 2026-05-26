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

from gtest_quiz.bank_epoch import current_bank_version, current_model_name
from gtest_quiz.question_quality import build_duplicate_index, is_probable_duplicate, validate_generated_question


BANK_PATH = Path("bank/question_bank.jsonl")
STATIC_BANK_PATH = Path("frontend/src/question-bank.json")
REQUIRED_METADATA = (
    "id",
    "source",
    "created_at",
    "domain",
    "chapter_group",
    "chapter_id",
    "difficulty",
    "question",
    "choices",
    "correct_index",
    "explanation",
    "syllabus",
    "bank_version",
)
REQUIRED_PROVENANCE = (
    "model",
    "prompt_version",
    "generated_at",
    "validator_score",
    "validator_reasons",
    "review_score",
    "review_reasons",
    "syllabus_node",
    "concepts",
    "bank_version",
)
MIN_EXPLANATION_LENGTH = 120
LEGACY_ID_PREFIXES = ("Q_T_", "Q_L_")
LEGACY_SOURCES = {"sample_seed", "content_factory"}


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
    expected_bank_version = current_bank_version()
    expected_model = current_model_name()
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
        if qid.startswith(LEGACY_ID_PREFIXES):
            errors.append(f"{path}:{line_no}: legacy id is not allowed in active bank: {qid}")

        choices = row.get("choices", [])
        correct_index = row.get("correct_index", -1)
        if not isinstance(choices, list) or len(choices) != 4:
            errors.append(f"{path}:{line_no}: choices must contain exactly four items")
        if correct_index not in {0, 1, 2, 3}:
            errors.append(f"{path}:{line_no}: correct_index must be 0..3")

        for field in REQUIRED_METADATA:
            if not str(row.get(field, "")).strip():
                errors.append(f"{path}:{line_no}: missing metadata field {field}")
        if str(row.get("source", "")) in LEGACY_SOURCES:
            errors.append(f"{path}:{line_no}: legacy source is not allowed: {row.get('source')}")
        if row.get("bank_version") != expected_bank_version:
            errors.append(f"{path}:{line_no}: bank_version must be {expected_bank_version}")

        provenance = row.get("provenance")
        if not isinstance(provenance, dict):
            errors.append(f"{path}:{line_no}: provenance must be an object")
            provenance = {}
        for field in REQUIRED_PROVENANCE:
            if field not in provenance:
                errors.append(f"{path}:{line_no}: missing provenance field {field}")
        if provenance.get("model") != expected_model:
            errors.append(f"{path}:{line_no}: provenance.model must be {expected_model}")
        if provenance.get("bank_version") != expected_bank_version:
            errors.append(f"{path}:{line_no}: provenance.bank_version must be {expected_bank_version}")
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


def validate_static_bank(path: Path = STATIC_BANK_PATH) -> List[str]:
    if not path.exists():
        return [f"missing static bank: {path}"]
    expected_bank_version = current_bank_version()
    errors: List[str] = []
    payload = json.loads(path.read_text(encoding="utf-8"))
    meta = payload.get("meta", {})
    questions = payload.get("questions", [])
    if meta.get("bank_version") != expected_bank_version:
        errors.append(f"{path}: meta.bank_version must be {expected_bank_version}")
    if int(meta.get("question_count", -1)) != len(questions):
        errors.append(f"{path}: question_count does not match questions length")
    if not str(meta.get("content_hash", "")).strip():
        errors.append(f"{path}: meta.content_hash is required")
    if "generated_at" in meta or "git_commit" in meta:
        errors.append(f"{path}: tracked static bank must not contain generated_at or git_commit")
    for index, row in enumerate(questions, start=1):
        if str(row.get("id", "")).startswith(LEGACY_ID_PREFIXES):
            errors.append(f"{path}: question {index}: legacy id is not allowed")
        if row.get("bank_version") != expected_bank_version:
            errors.append(f"{path}: question {index}: bank_version must be {expected_bank_version}")
    return errors


def main() -> None:
    errors = validate_question_bank() + validate_static_bank()
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"question bank ok: {BANK_PATH}")


if __name__ == "__main__":
    main()
