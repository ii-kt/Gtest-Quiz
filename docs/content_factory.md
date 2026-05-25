# Content Factory

The content factory is the current generation pipeline for maintaining the G検定 question bank. Older refill scripts live under `tools/legacy/` and are not part of the normal workflow.

## Pipeline

1. Build syllabus coverage targets from `bank/meta.json` and the existing question bank.
2. Generate one schema-constrained candidate per target using `GeneratedQuestionSpec`.
3. Validate structure, explanation length, difficulty, answer index, choice quality, and duplicates.
4. Accept high-quality candidates into `bank/question_bank.jsonl`.
5. Queue borderline or rejected candidates in `bank/generated_review_queue.jsonl`.
6. Write provenance to `bank/question_provenance.jsonl` when items are accepted or promoted.
7. Save refill metadata to `bank/meta.json` and rebuild `frontend/src/question-bank.json` for the PWA.

The first pass fills chapters below the per-chapter floor. After all chapters reach the floor, daily refill continues with a small rotating target set, so a full 55 chapter x 10 question bank still receives new questions.

## Provenance

Accepted generated questions include:

- model name
- prompt version
- validator score
- validator reasons
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

The scheduled GitHub Actions job runs once per day at `17 0 * * *` and uses `DAILY_TARGET=50` by default. Manual dispatch supports `reset_and_seed`, `seed`, `daily`, and `replace`. The default text generation model is `gemini-3.5-flash`; `GEMINI_MODEL` may override it explicitly, but there is no implicit fallback to older models.

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
