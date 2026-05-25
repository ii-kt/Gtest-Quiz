# Modernization Roadmap

This project is being moved from a demo-grade quiz app to a maintainable offline-first learning product. The current production path is the static PWA in `frontend/src/`; backend and generation tooling support validation, future sync, and local experiments.

## Phase 0 - Stabilize the Core (implemented)

- Stop leaking answer keys from `GET /quiz/next`.
- Add stricter Pydantic request validation.
- Store bearer tokens as SHA-256 fingerprints instead of raw secrets for newly issued tokens.
- Add elapsed-time capture and richer answer results.
- Move mutable runtime state to `.runtime/` instead of writing into source directories.
- Introduce an adaptive selection engine using unseen priority, chapter mastery, review urgency, and difficulty fit.
- Replace the minimal frontend with a responsive practice cockpit: stats, weak-chapter map, recent-answer timeline, loading states, and disabled states.
- Move Gemini refill generation toward the GA `google-genai` SDK with Pydantic structured output.

## Phase 1 - API Platform (completed)

- Add an ASGI/FastAPI adapter with OpenAPI docs while keeping the stdlib server as a zero-dependency fallback. (implemented)
- Split endpoints into versioned routers: auth, quiz, analytics, content, operations. (implemented)
- Add contract tests generated from the OpenAPI schema. (implemented through `docs/api/openapi_contract_v1.json`)
- Add CI gates for unit, integration, E2E, scoped coverage, schema drift, and question-bank validation. (implemented; coverage scope is documented in `.coveragerc`)
- Keep legacy HTTP routes available only as compatibility/local validation support.
- Repair question-bank JSON corruption uncovered by the new validation gate.

## UI Quality Track (parallel)

- Treat the quiz screen as the product, not a landing page.
- Keep the first viewport focused on practice state: current question, progress, weak chapters, recent attempts, and connection/auth status.
- Add small interaction improvements continuously: disabled states, keyboard answer input, loading indicators, focus states, mobile density checks, and answer-state clarity.
- Avoid decorative UI that does not help repeated practice.

## Phase 2 - Learning Intelligence (completed)

- Replace heuristic mastery with a calibrated model combining Bayesian accuracy, response time, recency, and difficulty. (implemented as `adaptive_mastery_v2`)
- Add spaced repetition scheduling at question and chapter levels. (implemented with `learning_items`)
- Build a benchmark set for G検定 coverage, hallucination resistance, duplicate detection, and explanation quality. (implemented through policy benchmark and content-factory validators)
- Add explainable recommendation traces for debugging but keep the learner UI compact. (implemented in `QuestionDTO.learning.explain`)
- Surface learning plan through `/api/v1/learning/plan`.
- Show tracked items and due reviews in the UI.

## Phase 3 - Content Factory (completed)

- Migrate all generation to `google-genai` structured output. (implemented via `GeminiQuestionGenerator`)
- Add schema-first generation, validator feedback loops, duplicate clustering, and syllabus coverage balancing. (implemented in `gtest_quiz.content_factory`)
- Add review queues for low-confidence generated questions. (implemented by `tools/review_generated_queue.py`; `bank/generated_review_queue.jsonl` is updated when the scheduled/manual quality workflow queues items)
- Track provenance for generated questions: source, model, prompt version, validator score, and syllabus node. (embedded provenance and `bank/question_provenance.jsonl` are created for generated/promoted items; legacy seed questions carry normalized metadata fields)
- Add dry-run, Gemini-backed factory run, queue summary, and promotion CLIs.

## Phase 4 - Productization (completed)

- Add a proper learner-session model for optional backend use, token expiry, refresh revocation, and migration scripts. (implemented with one-click sessions, hashed session tokens, `sessions`, and `tools/migrate_storage.py`; the static PWA no longer displays or stores a learner id)
- Add PWA offline practice, import/export, and mobile-first QA. (implemented as a static offline PWA with cached `question-bank.json`, device-local learning state, and file-based export/import)
- Add observability: structured logs, request IDs, latency metrics, content-quality metrics, and audit events. (implemented in FastAPI middleware, stdlib fallback, SQLite metrics, and audit tables)
- Package deployment profiles for local, classroom, and hosted operation. (implemented under `deploy/profiles/`)

## Phase 5 - Precision Tuning (completed foundation)

- Run learner simulations against the item bank to tune selection weights. (implemented in `tools/benchmark_learning_policy.py`)
- Compare adaptive sequencing against random and chapter-balanced baselines. (implemented with `--compare`)
- Add A/B hooks for selection policies. (implemented with `learning_policy_v1` assignment and `/api/v1/learning/policy`)
- Maintain a release rubric: answer-key safety, syllabus coverage, generation quality, UI usability, and recovery paths. (implemented in `docs/release_rubric.md` and `tools/release_readiness.py`; full release gating also includes pytest coverage and e2e)
