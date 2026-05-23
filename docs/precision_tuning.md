# Precision Tuning

Phase 5 keeps learning quality measurable instead of relying on intuition.

## Policies

- `adaptive_mastery_v2`: production policy using mastery, review urgency, weakness, difficulty fit, and jitter.
- `chapter_balanced_v1`: baseline that prioritizes chapters with fewer attempts.
- `random_baseline_v1`: random baseline for regression detection.

## A/B Hook

- `GET /api/v1/learning/policy` returns the active policy for the learner.
- `POST /api/v1/learning/policy` sets a policy variant.
- Setting `GTEST_POLICY_EXPERIMENT=learning_policy_v1` enables deterministic assignment for new users.

## Simulation

```bash
python tools/benchmark_learning_policy.py --compare
```

The comparison reports coverage, scheduled items, review-ready items, accuracy, and deltas against baselines.

## Release Gate

```bash
python tools/release_readiness.py
```

The rubric checks answer-key safety, syllabus coverage, generation quality surface, PWA recovery paths, observability, deployment profiles, and precision benchmark thresholds.
