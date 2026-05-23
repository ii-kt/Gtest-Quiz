# Learning Policy

The active policy is `adaptive_mastery_v2`.

## Signals

- Correctness
- Response time relative to expected time by difficulty
- Item difficulty
- Wilson lower bound for conservative mastery
- Chapter-level accuracy and speed
- Scheduled review due time

## Scheduling

Each answered question gets a learning item with:

- `easiness`
- `interval_hours`
- `due_at`
- `repetitions`
- `lapses`
- `last_grade`

Wrong answers reset repetitions and schedule a near-term review. Correct answers increase the interval according to easiness and difficulty.

## Selection

The selector scores each candidate with:

- due review priority
- new item priority
- weak chapter priority
- question mastery gap
- target difficulty fit

The public trace is returned in `QuestionDTO.learning.explain` so the recommendation can be debugged without exposing answers.
