# Release Rubric

Phase 5 keeps release quality measurable. A release is ready only when every gate below is green.

## Required Gates

- Answer-key safety: server-backed API question payloads must not expose `correct_index` or `explanation`; the static offline bank intentionally includes them so the iPhone-only PWA can grade answers without a server.
- Syllabus coverage: the bank must validate, include multiple chapters, and keep difficulty distribution visible.
- Generation quality: content-factory validators and duplicate checks must pass before generated items are promoted.
- UI usability: the browser app must include a static PWA shell, cached question bank, export/import, loading states, and device-local recovery.
- Recovery paths: learner data export/import must work inside the static PWA, while backend audit logs remain available for optional server-backed tooling.
- Precision tuning: adaptive policy benchmarks must run against random and chapter-balanced baselines.
- Operations: request IDs, structured logs, metrics, audit events, and deployment profiles must be present.

## Commands

```bash
python tools/validate_question_bank.py
pytest tests/contracts
python tools/benchmark_learning_policy.py --compare
python tools/release_readiness.py
pytest
```
