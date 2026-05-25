from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.bank_epoch import current_bank_version, current_model_name
from gtest_quiz.content_factory import PROVENANCE_PATH, QUESTION_BANK_PATH, REVIEW_QUEUE_PATH, _jsonl_append, domain_for_chapter_group
from gtest_quiz.question_quality import validate_generated_question


def load_queue(path: Path = REVIEW_QUEUE_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            items.append(json.loads(raw))
    return items


def summarize_queue(path: Path = REVIEW_QUEUE_PATH) -> Dict[str, Any]:
    items = load_queue(path)
    by_decision: Dict[str, int] = {}
    for item in items:
        decision = str(item.get("decision", "unknown"))
        by_decision[decision] = by_decision.get(decision, 0) + 1
    return {"total": len(items), "by_decision": dict(sorted(by_decision.items()))}


def promote(index: int, *, queue_path: Path = REVIEW_QUEUE_PATH, bank_path: Path = QUESTION_BANK_PATH) -> Dict[str, Any]:
    items = load_queue(queue_path)
    if index < 0 or index >= len(items):
        raise IndexError("queue index out of range")
    item = items[index]
    candidate = item.get("candidate")
    target = item.get("target", {})
    if not isinstance(candidate, dict):
        raise ValueError("queue item has no candidate")
    bank_version = str(item.get("bank_version") or current_bank_version())
    validation = validate_generated_question(candidate, min_explanation_length=120)
    if not validation.is_valid:
        raise ValueError(f"candidate is not promotable: {validation.reasons}")

    record = {
        "id": f"REVIEW_{index}_{abs(hash(candidate.get('question', ''))) % 100000}",
        "source": "review_promoted",
        "created_at": item.get("queued_at", ""),
        "bank_version": bank_version,
        "domain": domain_for_chapter_group(str(target.get("chapter_group", ""))),
        "chapter_group": target.get("chapter_group", ""),
        "chapter_id": target.get("chapter_id", candidate.get("syllabus_node", "")),
        "difficulty": candidate.get("difficulty", "standard"),
        "question": candidate["question"],
        "choices": candidate["choices"],
        "correct_index": int(candidate["correct_index"]),
        "explanation": candidate["explanation"],
        "syllabus": "G2024_v1.3",
        "provenance": {
            "model": item.get("model", current_model_name()),
            "prompt_version": item.get("prompt_version", ""),
            "generated_at": item.get("queued_at", ""),
            "bank_version": bank_version,
            "validator_score": validation.score,
            "validator_reasons": validation.reasons,
            "syllabus_node": candidate.get("syllabus_node", target.get("chapter_id", "")),
            "concepts": candidate.get("concepts", []),
            "review_queue_index": index,
        },
    }
    _jsonl_append(bank_path, record)
    _jsonl_append(PROVENANCE_PATH, {"id": record["id"], **record["provenance"]})
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or promote generated question review queue")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--promote", type=int)
    args = parser.parse_args()
    if args.promote is not None:
        print(json.dumps(promote(args.promote), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summarize_queue(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
