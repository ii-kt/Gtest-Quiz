# Content Factory

The content factory is the Phase 3 generation pipeline for maintaining the G検定 question bank.

## Pipeline

1. Build syllabus coverage targets from `bank/meta.json` and the existing question bank.
2. Generate one schema-constrained candidate per target using `GeneratedQuestionSpec`.
3. Validate structure, explanation length, difficulty, answer index, choice quality, and duplicates.
4. Accept high-quality candidates into `bank/question_bank.jsonl`.
5. Queue borderline or rejected candidates in `bank/generated_review_queue.jsonl`.
6. Write provenance to `bank/question_provenance.jsonl`.

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
python tools/run_content_factory.py --target 20 --model gemini-2.5-flash-lite
```

Review queue summary:

```bash
python tools/review_generated_queue.py --summary
```

Promote a reviewed candidate:

```bash
python tools/review_generated_queue.py --promote 0
```
