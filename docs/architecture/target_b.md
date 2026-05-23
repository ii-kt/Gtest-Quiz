# Target Architecture (/goal B)

## Phase 1: Architecture
- Backend application boundary: `backend/app/`
- Runnable HTTP adapter: `backend/app/main.py` (`run`, `create_server`)
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
- ASGI/OpenAPI adapter: `backend/app/asgi.py`
- Versioned API routers: `backend/app/api/` (`/api/v1`)
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
- Service/persistence split:
  - Domain/application service: `backend/app/services.py`
  - SQLite persistence: `backend/app/storage.py`
- Frontend shell: `frontend/src/index.html`
- Domain reuse from existing quiz assets: `gtest_quiz` (`meta`, `models`, `question_bank`)

## Phase 2: Core Features
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
- `POST /auth/start`: one-click learner session creation + bearer token issuance
- `POST /auth/refresh`: active session refresh + previous-token revocation
=======
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
>>>>>>> theirs
=======
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
>>>>>>> theirs
=======
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
>>>>>>> theirs
=======
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
>>>>>>> theirs
=======
- `POST /auth/register`: user creation + bearer token issuance
- `POST /auth/login`: existing user login + token rotation
>>>>>>> theirs
- `GET /quiz/next`: adaptive question selection
  1. unseen question priority
  2. weakest chapter priority
  3. chapter-balance fallback via `MetaManager`
- `POST /quiz/answer`: answer validation + usage persistence (`meta.json`) + user answer history (`sqlite`)
- `GET /quiz/stats`: global usage + per-user stats

## Phase 3: UI Refresh
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
- Static offline browser UI (`frontend/src/index.html`)
- Credential-free, device-local learner identity
- Immediate correct/incorrect feedback and running score
- Local progress, due review count, and mastery display
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
- API-driven browser UI (`frontend/src/index.html`)
- Explicit auth flow (login/register form)
- Immediate correct/incorrect feedback and running score
- Auth state and per-user total answer count display
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs

## Phase 4: Operational Quality
- Unit/integration/backend/frontend/e2e tests via `pytest`
- HTTP-level backend tests for auth/quiz/stats/error codes
- CI quality gates (Python 3.10/3.11/3.12) + release readiness workflow
- Coverage gate enabled in CI/release checks
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours

## Phase 5: Productization and Precision
- One-click learner sessions, hashed session tokens, session expiry, refresh revocation, and idempotent SQLite migrations
- Static offline PWA frontend with service worker, cached `question-bank.json`, device-local learning state, and file-based export/import
- Observability across FastAPI and stdlib adapters: request IDs, latency metrics, structured logs, audit events
- Deployment profiles for local, classroom, and hosted operation
- Adaptive policy compared against random and chapter-balanced baselines with `/learning/policy` A/B hooks
- Release rubric and automated readiness gate (`tools/release_readiness.py`)
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
