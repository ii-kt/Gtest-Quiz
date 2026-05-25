from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol

from pydantic import BaseModel, Field

from gtest_quiz.bank_epoch import DEFAULT_GEMINI_MODEL, DEFAULT_QUESTION_BANK_EPOCH
from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank
from gtest_quiz.question_quality import (
    ValidationResult,
    build_duplicate_index,
    is_probable_duplicate,
    validate_generated_question,
)


PROMPT_VERSION = "gtest_factory_gemini35_v1_2026-05-26"
QUESTION_BANK_PATH = Path("bank/question_bank.jsonl")
REVIEW_QUEUE_PATH = Path("bank/generated_review_queue.jsonl")
PROVENANCE_PATH = Path("bank/question_provenance.jsonl")
LEGAL_CHAPTER_GROUPS = {"AIに関する法律と契約", "AI倫理・AIガバナンス"}


class GeneratedQuestionSpec(BaseModel):
    question: str = Field(min_length=18)
    choices: List[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=120)
    difficulty: str = Field(pattern="^(basic|standard|advanced)$")
    syllabus_node: str = Field(min_length=1)
    concepts: List[str] = Field(default_factory=list)
    source_hint: str = ""


class QuestionGenerator(Protocol):
    def generate(self, prompt: str, schema: type[GeneratedQuestionSpec]) -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class FactoryConfig:
    model_name: str = DEFAULT_GEMINI_MODEL
    prompt_version: str = PROMPT_VERSION
    target_accepts: int = 80
    min_explanation_length: int = 120
    review_threshold: int = 75
    max_attempts_per_target: int = 3
    per_chapter_floor: int = 10
    allow_over_floor_growth: bool = True
    bank_version: str = DEFAULT_QUESTION_BANK_EPOCH
    mode: str = "daily"
    max_runtime_minutes: int = 25
    question_bank_path: Path = QUESTION_BANK_PATH
    review_queue_path: Path = REVIEW_QUEUE_PATH
    provenance_path: Path = PROVENANCE_PATH


@dataclass
class FactoryStats:
    generated: int = 0
    accepted: int = 0
    queued_for_review: int = 0
    rejected: int = 0
    duplicates: int = 0
    errors: int = 0
    targets: int = 0
    api_call_count: int = 0
    rate_limit_errors: int = 0


@dataclass(frozen=True)
class CoverageTarget:
    chapter_group: str
    chapter_id: str
    current_count: int
    target_count: int
    priority: float
    rotation_score: int = 0


@dataclass(frozen=True)
class CandidateDecision:
    action: str
    validation: ValidationResult
    duplicate: bool
    reasons: List[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jsonl_append(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def domain_for_chapter_group(chapter_group: str) -> str:
    return "法律分野" if chapter_group in LEGAL_CHAPTER_GROUPS else "技術分野"


def build_generation_prompt(target: CoverageTarget, prompt_version: str = PROMPT_VERSION) -> str:
    return f"""
あなたはJDLA G検定の専門作問者です。
prompt_version: {prompt_version}

目的:
- 受験者の理解度を測る高品質な4択問題を1問作る
- 暗記だけでなく概念の違い、実務上の判断、代表的な落とし穴を問う
- 誤答はもっともらしいが、解説で明確に区別できるものにする
- 単純な用語暗記ではなく、概念理解・比較・適用判断を問う

出力制約:
- response_schema に完全準拠
- 正解は1つ
- explanation は120文字以上
- explanation は「正解理由」と「不正解理由」または誤答との差分を含める
- syllabus_node には対象項目名を入れる

対象大分類: {target.chapter_group}
対象項目: {target.chapter_id}
現在の問題数: {target.current_count}
目標問題数: {target.target_count}
""".strip()


def load_existing_items(path: Path = QUESTION_BANK_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                items.append(data)
    return items


def _daily_rotation_score(chapter_id: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    digest = hashlib.sha256(f"{today}:{chapter_id}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def build_coverage_targets(
    meta: MetaManager,
    existing_items: Iterable[Dict[str, Any]],
    per_chapter_floor: int = 10,
    allow_over_floor_growth: bool = True,
) -> List[CoverageTarget]:
    counts: Dict[str, int] = {}
    groups: Dict[str, str] = {}
    for item in existing_items:
        chapter_id = str(item.get("chapter_id", ""))
        if not chapter_id:
            continue
        counts[chapter_id] = counts.get(chapter_id, 0) + 1
        groups.setdefault(chapter_id, str(item.get("chapter_group", "")))

    targets: List[CoverageTarget] = []
    chapters = meta.meta.get("chapters", {})
    for _group_key, group_val in chapters.items():
        group_label = str(group_val.get("label", ""))
        subchapters = group_val.get("subchapters", {})
        if not isinstance(subchapters, dict):
            continue
        for _sub_key, sub_val in subchapters.items():
            chapter_id = str(sub_val.get("label", ""))
            if not chapter_id:
                continue
            current = counts.get(chapter_id, 0)
            target_count = max(per_chapter_floor, int(float(sub_val.get("weight", 1.0)) * per_chapter_floor))
            deficit = max(0, target_count - current)
            rotation_score = _daily_rotation_score(chapter_id)
            if deficit > 0:
                priority = deficit / max(1, target_count)
            elif allow_over_floor_growth:
                surplus = current - target_count
                priority = float(sub_val.get("weight", 1.0)) / max(1, surplus + 1)
                target_count = current + 1
            else:
                priority = 0.0
            targets.append(
                CoverageTarget(
                    chapter_group=groups.get(chapter_id, group_label),
                    chapter_id=chapter_id,
                    current_count=current,
                    target_count=target_count,
                    priority=priority,
                    rotation_score=rotation_score,
                )
            )

    for chapter_id, current in counts.items():
        if not any(target.chapter_id == chapter_id for target in targets):
            targets.append(
                CoverageTarget(
                    chapter_group=groups.get(chapter_id, ""),
                    chapter_id=chapter_id,
                    current_count=current,
                    target_count=max(per_chapter_floor, current),
                    priority=0.0,
                    rotation_score=_daily_rotation_score(chapter_id),
                )
            )

    return sorted(targets, key=lambda t: (-t.priority, t.current_count, t.rotation_score, t.chapter_id))


def decide_candidate(
    data: Dict[str, Any],
    *,
    duplicate_index: Any,
    min_explanation_length: int,
    review_threshold: int,
) -> CandidateDecision:
    validation = validate_generated_question(data, min_explanation_length=min_explanation_length)
    duplicate = is_probable_duplicate(str(data.get("question", "")), duplicate_index)
    reasons = list(validation.reasons)
    if duplicate:
        reasons.append("probable duplicate")
    if duplicate:
        return CandidateDecision("duplicate", validation, duplicate, reasons)
    if validation.is_valid:
        return CandidateDecision("accept", validation, duplicate, reasons)
    if validation.score >= review_threshold:
        return CandidateDecision("review", validation, duplicate, reasons)
    return CandidateDecision("reject", validation, duplicate, reasons)


def to_question_record(
    data: Dict[str, Any],
    *,
    target: CoverageTarget,
    config: FactoryConfig,
    validation: ValidationResult,
) -> Dict[str, Any]:
    stamp = int(time.time() * 1000)
    return {
        "id": f"AUTO_{stamp}_{abs(hash(data.get('question', ''))) % 100000}",
        "source": "gemini35_content_factory",
        "created_at": _now_iso(),
        "bank_version": config.bank_version,
        "domain": domain_for_chapter_group(target.chapter_group),
        "chapter_group": target.chapter_group,
        "chapter_id": target.chapter_id,
        "difficulty": str(data.get("difficulty", "standard")),
        "question": str(data.get("question", "")),
        "choices": [str(choice) for choice in data.get("choices", [])],
        "correct_index": int(data.get("correct_index", 0)),
        "explanation": str(data.get("explanation", "")),
        "syllabus": "G2024_v1.3",
        "provenance": {
            "model": config.model_name,
            "prompt_version": config.prompt_version,
            "bank_version": config.bank_version,
            "validator_score": validation.score,
            "validator_reasons": validation.reasons,
            "syllabus_node": str(data.get("syllabus_node", target.chapter_id)),
            "concepts": list(data.get("concepts", [])),
            "generated_at": _now_iso(),
        },
    }


class ContentFactory:
    def __init__(self, config: FactoryConfig, generator: QuestionGenerator) -> None:
        self.config = config
        self.generator = generator

    def run(self, meta_path: str = "bank/meta.json") -> FactoryStats:
        meta = MetaManager(meta_path)
        meta.load()
        existing = load_existing_items(self.config.question_bank_path)
        duplicate_index = build_duplicate_index(existing)
        targets = [
            target
            for target in build_coverage_targets(
                meta,
                existing,
                per_chapter_floor=self.config.per_chapter_floor,
                allow_over_floor_growth=self.config.allow_over_floor_growth,
            )
            if target.priority > 0
        ]

        stats = FactoryStats(targets=len(targets))
        accepted_records: List[Dict[str, Any]] = []
        deadline = time.monotonic() + (self.config.max_runtime_minutes * 60)

        target_index = 0
        while targets and stats.accepted < self.config.target_accepts and time.monotonic() < deadline:
            target = targets[target_index % len(targets)]
            target_index += 1
            if time.monotonic() >= deadline:
                break
            if stats.accepted >= self.config.target_accepts:
                break
            for _attempt in range(self.config.max_attempts_per_target):
                if time.monotonic() >= deadline:
                    break
                if stats.accepted >= self.config.target_accepts:
                    break
                prompt = build_generation_prompt(target, self.config.prompt_version)
                try:
                    data = self.generator.generate(prompt, GeneratedQuestionSpec)
                    stats.generated += 1
                except Exception as e:
                    stats.errors += 1
                    self._queue_error(target, str(e))
                    continue

                decision = decide_candidate(
                    data,
                    duplicate_index=duplicate_index,
                    min_explanation_length=self.config.min_explanation_length,
                    review_threshold=self.config.review_threshold,
                )
                if decision.action == "duplicate":
                    stats.duplicates += 1
                    continue
                if decision.action == "reject":
                    stats.rejected += 1
                    self._queue_review(target, data, decision)
                    continue
                if decision.action == "review":
                    stats.queued_for_review += 1
                    self._queue_review(target, data, decision)
                    continue

                record = to_question_record(data, target=target, config=self.config, validation=decision.validation)
                _jsonl_append(self.config.question_bank_path, record)
                _jsonl_append(self.config.provenance_path, {"id": record["id"], **record["provenance"]})
                accepted_records.append(record)
                stats.accepted += 1
                duplicate_index = build_duplicate_index([*existing, *accepted_records])
                break

        if stats.generated or stats.accepted or stats.queued_for_review or stats.rejected or stats.duplicates or stats.errors:
            stats.api_call_count = int(getattr(self.generator, "api_call_count", stats.generated))
            stats.rate_limit_errors = int(getattr(self.generator, "rate_limit_errors", 0))
            total_questions = len(load_existing_items(self.config.question_bank_path))
            meta.meta["bank_version"] = self.config.bank_version
            meta.meta["content_factory"] = {
                "last_refill_at": _now_iso(),
                "model": self.config.model_name,
                "bank_version": self.config.bank_version,
                "mode": self.config.mode,
                "prompt_version": self.config.prompt_version,
                "target_accepts": self.config.target_accepts,
                "generated": stats.generated,
                "accepted": stats.accepted,
                "queued_for_review": stats.queued_for_review,
                "rejected": stats.rejected,
                "duplicates": stats.duplicates,
                "errors": stats.errors,
                "targets": stats.targets,
                "api_call_count": stats.api_call_count,
                "rate_limit_errors": stats.rate_limit_errors,
            }
            meta.meta["question_bank"] = {
                "path": str(self.config.question_bank_path),
                "bank_version": self.config.bank_version,
                "total_questions": total_questions,
                "updated_at": _now_iso(),
            }
            if accepted_records:
                meta.meta["last_chapter_id"] = str(accepted_records[-1].get("chapter_id", ""))
            meta.save()

        return stats

    def _queue_review(self, target: CoverageTarget, data: Dict[str, Any], decision: CandidateDecision) -> None:
        _jsonl_append(
            self.config.review_queue_path,
            {
                "queued_at": _now_iso(),
                "target": target.__dict__,
                "candidate": data,
                "decision": decision.action,
                "score": decision.validation.score,
                "reasons": decision.reasons,
                "prompt_version": self.config.prompt_version,
                "model": self.config.model_name,
                "bank_version": self.config.bank_version,
            },
        )

    def _queue_error(self, target: CoverageTarget, error: str) -> None:
        _jsonl_append(
            self.config.review_queue_path,
            {
                "queued_at": _now_iso(),
                "target": target.__dict__,
                "decision": "error",
                "error": error,
                "prompt_version": self.config.prompt_version,
                "model": self.config.model_name,
                "bank_version": self.config.bank_version,
            },
        )


def question_to_model(data: Dict[str, Any]) -> Question:
    return Question.from_dict(data)
