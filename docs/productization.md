# Productization Notes

## Offline Static PWA

- The learner-facing app runs from static files only: `index.html`, `offline-app.js`, `question-bank.json`, `manifest.webmanifest`, icons, and `service-worker.js`.
- iPhone use does not require a PC-hosted server. Publish `frontend/src/` to static hosting, open the HTTPS URL once in Safari, then add it to the Home Screen.
- The Service Worker caches the app shell and the complete question bank for offline launch after first install.
- Learning state is stored on the device through `localStorage`.

## Local Learning State

- The browser state stores learner id, active policy, answer history, recent attempts, and spaced-repetition items.
- Export produces a `gtest_quiz_offline_export_v1` JSON bundle.
- Import accepts the offline bundle and can also ingest older answer bundles.
- Imported answer correctness is recomputed from `question-bank.json`; imported `correct` and chapter fields are not trusted.

## Static Question Bank

- `tools/build_static_pwa_assets.py` converts `bank/question_bank.jsonl` into `frontend/src/question-bank.json`.
- The static bank intentionally includes `correct_index` and `explanation` because the iPhone-only app has no server to reveal answers after submission.
- The API contract still keeps `GET /quiz/next` answer-safe for server-backed use.

## Backend Status

- The FastAPI/stdlib backend remains available for generation, validation, benchmarks, OpenAPI contracts, and future sync.
- Backend sessions, metrics, audit logs, and deployment profiles are no longer required for day-to-day iPhone practice.
