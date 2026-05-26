# Release Rubric

Phase 5 keeps release quality measurable. A release is ready only when the CI release gate is green: validation, static asset build, contract checks, scoped coverage, benchmark, `tools/release_readiness.py`, and e2e smoke.

## Required Gates

- Answer-key safety: server-backed API question payloads must not expose `correct_index` or `explanation`; the static offline bank intentionally includes them so the iPhone-only PWA can grade answers without a server.
- Syllabus coverage: the bank must validate, include multiple chapters, and keep difficulty distribution visible.
- Generation quality: content-factory validators, duplicate checks, choice-position distribution, legal/guideline source metadata, review score, and refill result assertions must pass before generated items are promoted.
- UI usability: the browser app must include a static PWA shell, network-first question bank updates, export/import, loading states, and device-local recovery.
- Recovery paths: learner data export/import must work inside the static PWA, while backend audit logs remain available for optional server-backed tooling.
- Precision tuning: adaptive policy benchmarks must run against random and chapter-balanced baselines.
- Operations: request IDs, structured logs, metrics, audit events, and deployment profiles must be present.
- Coverage scope: `.coveragerc` defines the maintained code included in the 70% gate. Legacy Streamlit, old generation scripts, API adapter glue, and future-hosting surfaces are documented but not treated as primary coverage targets.

## Commands

```bash
python tools/validate_question_bank.py
pytest tests/contracts
pytest tests/test_question_quality.py tests/test_content_factory.py tests/test_refill_pipeline.py tests/integration tests/backend tests/frontend -m "not e2e" --cov=gtest_quiz --cov=backend/app --cov-report=term-missing --cov-fail-under=70
python tools/benchmark_learning_policy.py --compare
python tools/release_readiness.py
pytest tests/e2e -m e2e
```

`tools/release_readiness.py` defaults to the production profile and fails when the active bank has fewer than `PRODUCTION_MIN_QUESTIONS` questions. During the Gemini 3.5 bootstrap epoch, use `READINESS_PROFILE=bootstrap` only to confirm the reset and early seed state before production readiness.
