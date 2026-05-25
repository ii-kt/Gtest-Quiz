"""CLI entrypoint for high-quality refill pipeline."""

from __future__ import annotations

from gtest_quiz.refill_pipeline import RefillConfig, run_refill


def main() -> None:
    config = RefillConfig(
        model_name="gemini-2.5-flash-lite",
        target_daily=5,
        max_retry=3,
        min_explanation_length=80,
    )
    stats = run_refill(config)
    print({
        "generated": stats.generated,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "duplicates": stats.duplicates,
        "errors": stats.errors,
    })


if __name__ == "__main__":
    main()
