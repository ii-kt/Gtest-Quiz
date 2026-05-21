# Release Runbook

## 1. Preconditions
- CI `CI` workflow green on default branch.
- Local test runs green (non-e2e and e2e).
- `bank/question_bank.jsonl` format sanity checked.

## 2. Versioning
1. Decide semantic version (`vMAJOR.MINOR.PATCH`).
2. Update changelog/notes in PR description.
3. Create annotated tag:
   ```bash
   git tag -a vX.Y.Z -m "release vX.Y.Z"
   git push origin vX.Y.Z
   ```

## 3. Quality Gates
- Non-e2e gate:
  ```bash
  pytest tests/test_question_quality.py tests/integration tests/backend tests/frontend -m "not e2e" --cov=gtest_quiz --cov=backend/app --cov-report=term-missing --cov-fail-under=70
  ```
- E2E gate:
  ```bash
  pytest tests/e2e -m e2e
  ```

## 4. Rollback
1. Revert problematic PR on main.
2. Create patch tag (`vX.Y.(Z+1)`).
3. Re-run release workflow.

## 5. Post-release Verification (Backend/Frontend Runtime)
- API boot check:
  ```bash
  ./scripts_run_backend.sh
  ```
- Health check:
  ```bash
  curl -s http://127.0.0.1:8000/health
  ```
- Auth + quiz smoke:
  1. Open `frontend/src/index.html` in browser (or static host)
  2. Login/Register with a username
  3. Fetch one question and submit one answer
- Verify counters:
  - `GET /quiz/stats` returns user `total_answers >= 1`
