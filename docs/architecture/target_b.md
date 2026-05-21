# Target Architecture (/goal B)

## Phase 1: Architecture
- Backend application boundary: `backend/app/`
- Runnable HTTP adapter: `backend/app/main.py` (`run`, `create_server`)
- Service/persistence split:
  - Domain/application service: `backend/app/services.py`
  - SQLite persistence: `backend/app/storage.py`
- Frontend shell: `frontend/src/index.html`
- Domain reuse from existing quiz assets: `gtest_quiz` (`meta`, `models`, `question_bank`)

## Phase 2: Core Features
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
- `GET /quiz/next`: adaptive question selection
  1. unseen question priority
  2. weakest chapter priority
  3. chapter-balance fallback via `MetaManager`
- `POST /quiz/answer`: answer validation + usage persistence (`meta.json`) + user answer history (`sqlite`)
- `GET /quiz/stats`: global usage + per-user stats

## Phase 3: UI Refresh
- API-driven browser UI (`frontend/src/index.html`)
- Explicit auth flow (login/register form)
- Immediate correct/incorrect feedback and running score
- Auth state and per-user total answer count display

## Phase 4: Operational Quality
- Unit/integration/backend/frontend/e2e tests via `pytest`
- HTTP-level backend tests for auth/quiz/stats/error codes
- CI quality gates (Python 3.10/3.11/3.12) + release readiness workflow
- Coverage gate enabled in CI/release checks
