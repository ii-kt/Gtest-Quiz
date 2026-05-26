from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.content_factory import (
    LEGAL_SOURCE_FIELDS,
    PROVENANCE_PATH,
    QUESTION_BANK_PATH,
    is_legal_target,
    review_generated_candidate,
    shuffle_choices_for_record,
)
from gtest_quiz.meta import MetaManager


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def normalize_active_bank() -> Dict[str, Any]:
    rows = _load_jsonl(QUESTION_BANK_PATH)
    normalized: List[Dict[str, Any]] = []
    dropped: List[str] = []
    target_position = 0

    for row in rows:
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        candidate = {
            **row,
            "syllabus_node": provenance.get("syllabus_node", row.get("chapter_id", "")),
            "concepts": provenance.get("concepts", []),
        }
        review_score, review_reasons = review_generated_candidate(candidate, min_explanation_length=120)
        legal_row = is_legal_target(str(row.get("chapter_group", "")), str(row.get("chapter_id", "")), str(row.get("domain", "")))
        missing_legal = [field for field in LEGAL_SOURCE_FIELDS if legal_row and not str(row.get(field, "")).strip()]
        if review_score < 95 or review_reasons or missing_legal:
            dropped.append(str(row.get("id", "")))
            continue

        choices, correct_index, shuffle_seed = shuffle_choices_for_record(
            [str(choice) for choice in row.get("choices", [])],
            int(row.get("correct_index", 0)),
            seed_material=f"{row.get('bank_version', '')}:normalize:{row.get('id', '')}:{row.get('question', '')}",
            desired_correct_index=target_position % 4,
        )
        target_position += 1
        row["choices"] = choices
        row["correct_index"] = correct_index
        provenance["review_score"] = review_score
        provenance["review_reasons"] = []
        provenance["accepted_with_review_warnings"] = False
        provenance["choice_shuffle_seed"] = shuffle_seed
        row["provenance"] = provenance
        normalized.append(row)

    _write_jsonl(QUESTION_BANK_PATH, normalized)
    _write_jsonl(PROVENANCE_PATH, [{"id": row["id"], **row["provenance"]} for row in normalized])
    meta = MetaManager("bank/meta.json")
    meta.load()
    if "question_bank" in meta.meta:
        meta.meta["question_bank"]["total_questions"] = len(normalized)
    meta.meta["normalization"] = {"kept": len(normalized), "dropped": len(dropped), "dropped_ids": dropped}
    meta.save()
    return {"kept": len(normalized), "dropped": len(dropped), "dropped_ids": dropped}


def main() -> None:
    print(json.dumps(normalize_active_bank(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
