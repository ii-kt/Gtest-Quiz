# Content Factory

The content factory is the current generation pipeline for maintaining the G検定 question bank. Older refill scripts live under `tools/legacy/` and are not part of the normal workflow.

## Pipeline

1. Build syllabus coverage targets from `bank/meta.json` and the existing question bank.
2. Generate one schema-constrained candidate per target using `GeneratedQuestionSpec`.
3. Validate structure, explanation length, difficulty, answer index, choice quality, duplicates, legal/guideline source metadata, and review score.
4. Accept high-quality candidates into `bank/question_bank.jsonl`.
5. Queue borderline or rejected candidates in `bank/generated_review_queue.jsonl`.
6. Write provenance to `bank/question_provenance.jsonl` when items are accepted or promoted.
7. Save refill metadata to `bank/meta.json` and rebuild `frontend/src/question-bank.json` for the PWA.

`reset_and_seed` is transactional: generation writes to `.next` JSONL files first, validates them, and only swaps them into the active bank after at least one accepted item passes validation. A failed reset does not destroy the current active bank. `replace` identifies low-quality candidates first, preserves their chapter/concept targets, and only removes old questions after replacements are accepted.

The first pass fills chapters below the per-chapter floor. After all chapters reach the floor, daily refill continues with a rotating target set, so a full 55 chapter x 10 question bank still receives new questions.

## Provenance

Accepted generated questions include:

- model name
- prompt version
- validator score
- validator reasons
- review score
- review reasons
- syllabus node
- generated timestamp
- concepts

## Commands

Dry-run:

```bash
python tools/run_content_factory.py --dry-run --target 1
```

Gemini-backed run:

```bash
python tools/auto_refill_quality.py
```

The scheduled GitHub Actions job runs once per day at `0 0 * * *` (09:00 JST) and uses `DAILY_TARGET=10` by default. Daily target sizing is adaptive: the previous accepted count, rate-limit count, API call count, and errors are saved to `bank/meta.json`, then the next daily run backs off after quota pressure and steps up after clean success. Manual dispatch supports `reset_and_seed`, `seed`, `daily`, `replace`, `build_to_complete`, `build_to_expanded`, and `validate_only`. The default text generation model is `gemini-3.5-flash`; `GEMINI_MODEL` may override it explicitly, but there is no implicit fallback to older models. When `ENFORCE_GEMINI35=true`, any other model fails the workflow. `tools/assert_refill_result.py` fails CI when a run silently accepts zero items without an explicit quota/rate-limit reason.

Manual `seed` / `build_to_complete` failures with `accepted=0` may not commit `bank/meta.json`, so their `last_refill_result` may not persist on `main`; use the GitHub Actions log to choose the next manual target. Scheduled `daily` runs with a rate-limit/quota signal can pass the assert gate even when `accepted=0`; if `bank/meta.json` is committed, the next daily run uses that persisted signal to reduce the target.

Accepted questions must have `review_score >= 95` and empty `review_reasons`. Choices are shuffled after generation, `correct_index` is recalculated, and `choice_shuffle_seed` is stored in provenance. Legal/guideline scoped questions must include `source_url`, `source_title`, `source_version`, `source_checked_at`, and `legal_basis`.

The active bank epoch is `gemini35_v1`. Old seed questions are removed from the active bank, and generated records must carry `bank_version`, `provenance.model`, and `provenance.bank_version`.

Review queue summary:

```bash
python tools/review_generated_queue.py --summary
```

Promote a reviewed candidate:

```bash
python tools/review_generated_queue.py --promote 0
```

After any accepted or promoted items:

```bash
python tools/validate_question_bank.py
python tools/build_static_pwa_assets.py
```
