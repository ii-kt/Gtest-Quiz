# Release Runbook

## 1. Preconditions
- CI `CI` workflow green on default branch.
- Local test runs green (non-e2e and e2e).
- `bank/question_bank.jsonl` format sanity checked.
- The current production path is the static PWA under `frontend/src/`. Backend adapters are local/future support unless a separate hosted-backend release is explicitly planned.

## 2. Versioning
1. Decide semantic version (`vMAJOR.MINOR.PATCH`).
2. Update changelog/notes in PR description.
3. Create annotated tag:
   ```bash
   git tag -a vX.Y.Z -m "release vX.Y.Z"
   git push origin vX.Y.Z
   ```

## 3. Quality Gates
- Question bank validation:
  ```bash
  python tools/validate_question_bank.py
  ```
- Static PWA asset generation:
  ```bash
  python tools/build_static_pwa_assets.py
  ```
- OpenAPI contract drift check:
  ```bash
  pytest tests/contracts
  ```
- Learning policy benchmark:
  ```bash
  python tools/benchmark_learning_policy.py --compare
  ```
- Release readiness rubric:
  ```bash
  python tools/release_readiness.py
  ```
- Storage migration smoke:
  ```bash
  python tools/migrate_storage.py --db .runtime/release_check.db
  ```
- Non-e2e gate:
  ```bash
  pytest tests/test_question_quality.py tests/test_content_factory.py tests/test_refill_pipeline.py tests/integration tests/backend tests/frontend -m "not e2e" --cov=gtest_quiz --cov=backend/app --cov-report=term-missing --cov-fail-under=70
  ```
- E2E gate:
  ```bash
  pytest tests/e2e -m e2e
  ```

`tools/release_readiness.py` is a rubric check, not the whole release gate. Coverage is enforced by the pytest-cov command above, with scope defined in `.coveragerc`.

## 4. Rollback
1. Revert problematic PR on main.
2. Create patch tag (`vX.Y.(Z+1)`).
3. Re-run release workflow.

## 5. Post-release Verification (Static PWA)
- Publish `frontend/src/` to the static host. For GitHub Pages, run the `Static PWA Pages` workflow and use the workflow output URL.
- Open the HTTPS URL on iPhone Safari.
- Add it to the Home Screen.
- Launch from the Home Screen icon.
- Verify:
  - A question appears without starting a PC server.
  - One answer updates local stats.
  - `エクスポート` downloads a `gtest_quiz_offline_export_v1` bundle.
  - Reloading while offline still opens the app after first install.
  - `question-bank.json` question count matches `bank/question_bank.jsonl`.
