"""Question quality validation and near-duplicate detection utilities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Set


WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\u3000\s、。，．,.;:!?！？()（）\[\]【】『』「」'\"`]+")


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    score: int
    reasons: List[str]


@dataclass(frozen=True)
class DuplicateIndex:
    exact_hashes: Set[str]
    normalized_hashes: Set[str]
    fingerprints: Set[str]


def _normalize_space(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.strip())


def normalize_question_text(text: str) -> str:
    text = _normalize_space(text)
    text = PUNCT_RE.sub("", text)
    return text.lower()


def exact_question_hash(text: str) -> str:
    return hashlib.sha256(_normalize_space(text).encode("utf-8")).hexdigest()


def normalized_question_hash(text: str) -> str:
    return hashlib.sha256(normalize_question_text(text).encode("utf-8")).hexdigest()


def fingerprint_tokens(text: str, n: int = 18) -> str:
    normalized = normalize_question_text(text)
    if not normalized:
        return ""
    tokens = [t for t in re.split(r"[^0-9a-zA-Z一-龥ぁ-んァ-ヶ]+", normalized) if t]
    if not tokens:
        return normalized[:80]
    return "|".join(tokens[:n])


def build_duplicate_index(items: Iterable[Dict[str, Any]]) -> DuplicateIndex:
    exact_hashes: Set[str] = set()
    normalized_hashes: Set[str] = set()
    fingerprints: Set[str] = set()

    for item in items:
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        exact_hashes.add(exact_question_hash(question))
        normalized_hashes.add(normalized_question_hash(question))
        fingerprints.add(fingerprint_tokens(question))

    return DuplicateIndex(
        exact_hashes=exact_hashes,
        normalized_hashes=normalized_hashes,
        fingerprints=fingerprints,
    )


def is_probable_duplicate(question: str, duplicate_index: DuplicateIndex) -> bool:
    exact_hash = exact_question_hash(question)
    if exact_hash in duplicate_index.exact_hashes:
        return True

    normalized_hash = normalized_question_hash(question)
    if normalized_hash in duplicate_index.normalized_hashes:
        return True

    fp = fingerprint_tokens(question)
    return bool(fp and fp in duplicate_index.fingerprints)


def _has_duplicate_choices(choices: Sequence[str]) -> bool:
    normalized = [normalize_question_text(choice) for choice in choices]
    normalized = [c for c in normalized if c]
    return len(normalized) != len(set(normalized))


def validate_generated_question(data: Dict[str, Any], min_explanation_length: int = 120) -> ValidationResult:
    reasons: List[str] = []
    score = 100

    question = str(data.get("question", "")).strip()
    choices = data.get("choices", [])
    explanation = str(data.get("explanation", "")).strip()
    difficulty = str(data.get("difficulty", "")).strip()

    try:
        correct_index = int(data.get("correct_index", -1))
    except Exception:
        correct_index = -1

    if not question:
        reasons.append("question is empty")
        score -= 50
    elif len(question) < 18:
        reasons.append("question is too short")
        score -= 20

    if not isinstance(choices, list) or len(choices) != 4:
        reasons.append("choices must contain exactly four items")
        score -= 50
        choices = []
    else:
        if any(not str(choice).strip() for choice in choices):
            reasons.append("choices contain empty text")
            score -= 25
        if _has_duplicate_choices([str(choice) for choice in choices]):
            reasons.append("choices are duplicated or near-duplicated")
            score -= 25
        if any(len(str(choice).strip()) < 2 for choice in choices):
            reasons.append("choice text is too short")
            score -= 10

    if correct_index not in {0, 1, 2, 3}:
        reasons.append("correct_index must be 0..3")
        score -= 40

    if len(explanation) < min_explanation_length:
        reasons.append("explanation is too short")
        score -= 20
    if explanation and not any(token in explanation for token in ("正解理由", "正解は", "適切です", "根拠")):
        reasons.append("explanation should include the reason for the correct answer")
        score -= 10
    if explanation and not any(token in explanation for token in ("不正解理由", "他の選択肢", "誤答", "差分")):
        reasons.append("explanation should distinguish incorrect choices")
        score -= 10

    if difficulty not in {"basic", "standard", "advanced"}:
        reasons.append("difficulty must be basic|standard|advanced")
        score -= 10

    if question and explanation and normalize_question_text(question) == normalize_question_text(explanation):
        reasons.append("explanation duplicates the question")
        score -= 20

    return ValidationResult(
        is_valid=(score >= 75 and not any(r.startswith("choices must") or r == "question is empty" for r in reasons)),
        score=max(score, 0),
        reasons=reasons,
    )
