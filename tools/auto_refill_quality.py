"""CLI entrypoint for the Gemini 3.5 Flash question-bank pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.bank_epoch import current_bank_version, current_model_name
from gtest_quiz.refill_pipeline import RefillConfig, run_refill


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _target_for_mode(mode: str, explicit_target: str | None) -> int:
    if explicit_target:
        try:
            return int(explicit_target)
        except ValueError as exc:
            raise SystemExit(f"invalid target: {explicit_target}") from exc
    if mode in {"seed", "reset_and_seed"}:
        return _env_int("INITIAL_TARGET_PER_RUN", 150)
    return _env_int("DAILY_TARGET", 50)


def _stats_payload(stats: Any) -> dict[str, Any]:
    return {
        "model_name": stats.model_name,
        "bank_version": stats.bank_version,
        "mode": stats.mode,
        "reset_performed": stats.reset_performed,
        "old_active_question_count": stats.old_active_question_count,
        "deleted_question_count": stats.deleted_question_count,
        "active_question_count_before": stats.active_question_count_before,
        "generated": stats.generated,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "duplicates": stats.duplicates,
        "errors": stats.errors,
        "queued_for_review": stats.queued_for_review,
        "api_call_count": stats.api_call_count,
        "rate_limit_errors": stats.rate_limit_errors,
        "active_question_count_after": stats.active_question_count_after,
        "new_active_question_count": stats.active_question_count_after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the current Gemini question-bank generation pipeline.")
    parser.add_argument("--mode", choices=["daily", "seed", "reset_and_seed", "replace"], default=os.getenv("GENERATION_MODE", "daily"))
    parser.add_argument("--target", default=os.getenv("GENERATION_TARGET"))
    args = parser.parse_args()

    model_name = current_model_name()
    bank_version = current_bank_version()
    target = _target_for_mode(args.mode, args.target)

    config = RefillConfig(
        model_name=model_name,
        target_daily=target,
        max_retry=_env_int("MAX_RETRY", 3),
        min_explanation_length=_env_int("MIN_EXPLANATION_LENGTH", 120),
        max_runtime_minutes=_env_int("MAX_RUNTIME_MINUTES", 25),
        mode=args.mode,
        bank_version=bank_version,
        reset_question_bank=_env_bool("RESET_QUESTION_BANK") or args.mode == "reset_and_seed",
    )
    stats = run_refill(config)
    print(json.dumps(_stats_payload(stats), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
