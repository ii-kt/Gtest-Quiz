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
        return {
            "rounds": 0,
            "accuracy": 0.0,
            "unique_questions": 0,
            "covered_chapters": 0,
            "scheduled_items": 0,
            "review_ready_items": 0,
            "policy": policy_variant,
            "bootstrap_empty_bank": True,
        }

    history: List[Dict[str, Any]] = []
    summary: Dict[str, Dict[str, Any]] = {}
    schedules: Dict[str, Dict[str, Any]] = {}
    covered_chapters = set()
    weak_chapter_revisits = 0
    due_review_hits = 0
    correct_count = 0
    simulation_rounds = min(rounds, max(len(bank) * 6, len(bank)))

    for idx in range(simulation_rounds):
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
        reason = selection.learning.reason if hasattr(selection.learning, "reason") else selection.learning.get("reason", "")
        if reason == "weak_chapter":
            weak_chapter_revisits += 1
        if reason == "review_due":
            due_review_hits += 1
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
    unique_questions = len(summary)
    repeat_rate = 1 - (unique_questions / len(history)) if history else 0.0
    expected_chapters = len({question.chapter_id for question in bank}) or 1
    coverage_ratio = len(covered_chapters) / expected_chapters
    unique_ratio = unique_questions / max(1, min(len(bank), len(history)))
    policy_balance_score = max(0.0, min(1.0, (coverage_ratio * 0.45) + (unique_ratio * 0.35) + ((1 - repeat_rate) * 0.20)))
    return {
        "rounds": len(history),
        "accuracy": round(correct_count / len(history), 4) if history else 0.0,
        "unique_questions": unique_questions,
        "covered_chapters": len(covered_chapters),
        "scheduled_items": len(schedules),
        "review_ready_items": due_reviews,
        "repeat_rate": round(repeat_rate, 4),
        "weak_chapter_revisit_rate": round(weak_chapter_revisits / len(history), 4) if history else 0.0,
        "due_review_hit_rate": round(due_review_hits / len(history), 4) if history else 0.0,
        "policy_balance_score": round(policy_balance_score, 4),
        "policy": policy_variant,
        "limited_by_bank_size": simulation_rounds < rounds,
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
            "adaptive_vs_random_balance": round(adaptive.get("policy_balance_score", 0) - random_baseline.get("policy_balance_score", 0), 4),
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
