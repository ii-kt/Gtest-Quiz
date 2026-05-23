from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from gtest_quiz.question_bank import get_all_questions


def chapter_catalog() -> List[Dict[str, Any]]:
    questions = get_all_questions()
    counts = Counter(q.chapter_id for q in questions)
    groups = {q.chapter_id: q.chapter_group for q in questions}
    domains = {q.chapter_id: q.domain for q in questions}
    return [
        {
            "chapter_id": chapter_id,
            "chapter_group": groups.get(chapter_id, ""),
            "domain": domains.get(chapter_id, ""),
            "question_count": count,
        }
        for chapter_id, count in sorted(counts.items())
    ]


def question_bank_summary() -> Dict[str, Any]:
    questions = get_all_questions()
    difficulties = Counter(q.difficulty for q in questions)
    domains = Counter(q.domain or "unknown" for q in questions)
    return {
        "total_questions": len(questions),
        "difficulty_counts": dict(sorted(difficulties.items())),
        "domain_counts": dict(sorted(domains.items())),
    }


def offline_question_pack(limit: int = 120) -> Dict[str, Any]:
    questions = get_all_questions()[:limit]
    return {
        "schema_version": "offline_pack_v1",
        "question_count": len(questions),
        "questions": [
            {
                "id": q.id,
                "domain": q.domain,
                "chapter_group": q.chapter_group,
                "chapter_id": q.chapter_id,
                "difficulty": q.difficulty,
                "question": q.question,
                "choices": q.choices,
            }
            for q in questions
        ],
    }
