from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.experiments import ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY, POLICY_VARIANTS, RANDOM_POLICY
from backend.app.learning import select_next_question, update_schedule
from gtest_quiz.question_bank import get_all_questions


def run_policy_benchmark(seed: int = 7, rounds: int = 160, policy_variant: str = ADAPTIVE_POLICY) -> Dict[str, Any]:
    random.seed(seed)
    bank = get_all_questions()
    if not bank:
        return {"rounds": 0, "error": "empty question bank"}

    history: List[Dict[str, Any]] = []
    summary: Dict[str, Dict[str, Any]] = {}
    schedules: Dict[str, Dict[str, Any]] = {}
    covered_chapters = set()
    correct_count = 0

    for idx in range(rounds):
        selection = select_next_question(
            bank,
            history=history,
            question_summary=summary,
            total_answers=idx,
            accuracy=(correct_count / idx) if idx else 0.0,
            policy_variant=policy_variant,
        )
        if selection is None:
            break
        q = selection.question
        covered_chapters.add(q.chapter_id)

        latent = 0.62 if q.difficulty == "basic" else 0.54 if q.difficulty == "standard" else 0.45
        seen = summary.get(q.id, {}).get("attempts", 0)
        correct = random.random() < min(0.92, latent + seen * 0.08)
        elapsed_ms = random.randint(9_000, 55_000)
        correct_count += 1 if correct else 0

        sched = update_schedule(schedules.get(q.id), correct=correct, elapsed_ms=elapsed_ms, difficulty=q.difficulty)
        schedules[q.id] = sched.__dict__
        attempts = int(summary.get(q.id, {}).get("attempts", 0)) + 1
        wrongs = int(summary.get(q.id, {}).get("wrongs", 0)) + (0 if correct else 1)
        summary[q.id] = {
            "attempts": attempts,
            "wrongs": wrongs,
            "last_correct": correct,
            "avg_elapsed_ms": elapsed_ms,
            "due_at": sched.due_at,
            **sched.__dict__,
        }
        history.append(
            {
                "question_id": q.id,
                "chapter_id": q.chapter_id,
                "correct": 1 if correct else 0,
                "elapsed_ms": elapsed_ms,
                "answered_at": sched.due_at,
            }
        )

    due_reviews = sum(1 for item in schedules.values() if item.get("repetitions", 0) > 0)
    return {
        "rounds": len(history),
        "accuracy": round(correct_count / len(history), 4) if history else 0.0,
        "unique_questions": len(summary),
        "covered_chapters": len(covered_chapters),
        "scheduled_items": len(schedules),
        "review_ready_items": due_reviews,
        "policy": policy_variant,
    }


def compare_policy_benchmarks(seed: int = 7, rounds: int = 160) -> Dict[str, Any]:
    results = {
        policy: run_policy_benchmark(seed=seed, rounds=rounds, policy_variant=policy)
        for policy in POLICY_VARIANTS
    }
    adaptive = results[ADAPTIVE_POLICY]
    random_baseline = results[RANDOM_POLICY]
    chapter_baseline = results[CHAPTER_BALANCED_POLICY]
    return {
        "seed": seed,
        "rounds": rounds,
        "results": results,
        "deltas": {
            "adaptive_vs_random_coverage": adaptive["covered_chapters"] - random_baseline["covered_chapters"],
            "adaptive_vs_random_scheduled": adaptive["scheduled_items"] - random_baseline["scheduled_items"],
            "adaptive_vs_chapter_accuracy": round(adaptive["accuracy"] - chapter_baseline["accuracy"], 4),
        },
        "recommended_policy": ADAPTIVE_POLICY,
    }


def main() -> None:
    if "--compare" in sys.argv:
        print(json.dumps(compare_policy_benchmarks(), ensure_ascii=False, indent=2))
        return
    print(json.dumps(run_policy_benchmark(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
