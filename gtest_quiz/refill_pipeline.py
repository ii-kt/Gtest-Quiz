"""Content refill pipeline backed by the schema-first content factory."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel

from gtest_quiz.bank_epoch import DEFAULT_GEMINI_MODEL, DEFAULT_QUESTION_BANK_EPOCH
from gtest_quiz.content_factory import (
    PROVENANCE_PATH,
    QUESTION_BANK_PATH,
    REVIEW_QUEUE_PATH,
    ContentFactory,
    FactoryConfig,
    FactoryStats,
    GeneratedQuestionSpec,
    load_existing_items,
)
from gtest_quiz.env import get_env, load_dotenv
from gtest_quiz.meta import MetaManager
from gtest_quiz.question_quality import validate_generated_question


class RefillConfig:
    def __init__(
        self,
        *,
        model_name: str = DEFAULT_GEMINI_MODEL,
        target_daily: int = 50,
        max_retry: int = 3,
        min_explanation_length: int = 120,
        sleep_seconds_on_429: float = 2.0,
        hard_stop_on_near_quota: bool = True,
        mode: str = "daily",
        bank_version: str = DEFAULT_QUESTION_BANK_EPOCH,
        max_runtime_minutes: int = 25,
        reset_question_bank: bool = False,
    ) -> None:
        self.model_name = model_name
        self.target_daily = target_daily
        self.max_retry = max_retry
        self.min_explanation_length = min_explanation_length
        self.sleep_seconds_on_429 = sleep_seconds_on_429
        self.hard_stop_on_near_quota = hard_stop_on_near_quota
        self.mode = mode
        self.bank_version = bank_version
        self.max_runtime_minutes = max_runtime_minutes
        self.reset_question_bank = reset_question_bank


class RefillStats:
    def __init__(self) -> None:
        self.generated = 0
        self.accepted = 0
        self.rejected = 0
        self.duplicates = 0
        self.errors = 0
        self.queued_for_review = 0
        self.api_call_count = 0
        self.rate_limit_errors = 0
        self.mode = ""
        self.model_name = ""
        self.bank_version = ""
        self.reset_performed = False
        self.old_active_question_count = 0
        self.deleted_question_count = 0
        self.active_question_count_before = 0
        self.active_question_count_after = 0

    @classmethod
    def from_factory(cls, stats: FactoryStats, *, config: RefillConfig) -> "RefillStats":
        item = cls()
        item.generated = stats.generated
        item.accepted = stats.accepted
        item.rejected = stats.rejected
        item.duplicates = stats.duplicates
        item.errors = stats.errors
        item.queued_for_review = stats.queued_for_review
        item.api_call_count = stats.api_call_count
        item.rate_limit_errors = stats.rate_limit_errors
        item.mode = config.mode
        item.model_name = config.model_name
        item.bank_version = config.bank_version
        return item


def _safe_parse_json(text: str) -> Optional[Dict[str, object]]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


def _load_generator(api_key: str, model_name: str) -> Tuple[str, Any]:
    try:
        from google import genai

        return "google-genai", genai.Client(api_key=api_key)
    except Exception:
        try:
            import google.generativeai as legacy_genai
        except Exception as e:
            raise RuntimeError("Install google-genai to use Gemini refill generation") from e

        legacy_genai.configure(api_key=api_key)
        return "legacy", legacy_genai.GenerativeModel(model_name)


class GeminiQuestionGenerator:
    def __init__(self, *, api_key: str, model_name: str, max_retry: int = 3, sleep_seconds: float = 0.4) -> None:
        self.model_name = model_name
        self.max_retry = max_retry
        self.sleep_seconds = sleep_seconds
        self.api_call_count = 0
        self.rate_limit_errors = 0
        self.generator_kind, self.generator = _load_generator(api_key, model_name)

    def generate(self, prompt: str, schema: type[GeneratedQuestionSpec]) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        for _ in range(self.max_retry):
            try:
                data = self._generate_once(prompt, schema)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e):
                    self.rate_limit_errors += 1
            time.sleep(self.sleep_seconds)
        if last_error:
            raise last_error
        raise RuntimeError("Gemini did not return a structured question")

    def _generate_once(self, prompt: str, schema: type[BaseModel]) -> Optional[Dict[str, Any]]:
        self.api_call_count += 1
        if self.generator_kind == "google-genai":
            response = self.generator.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                    "temperature": 0.62,
                },
            )
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, BaseModel):
                return parsed.model_dump()
            if isinstance(parsed, dict):
                return parsed
            return _safe_parse_json(getattr(response, "text", ""))

        response = self.generator.generate_content(prompt)
        return _safe_parse_json(getattr(response, "text", ""))


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "rate limit" in text or "quota" in text or "resource exhausted" in text


def _write_jsonl(path: Path, rows: list[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def reset_active_bank(*, meta_path: str = "bank/meta.json", bank_version: str = DEFAULT_QUESTION_BANK_EPOCH) -> Dict[str, int]:
    old_count = len(load_existing_items(QUESTION_BANK_PATH))
    for path in (QUESTION_BANK_PATH, REVIEW_QUEUE_PATH, PROVENANCE_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    meta = MetaManager(meta_path)
    meta.load()
    meta.meta["bank_version"] = bank_version
    meta.meta["quota_estimate"] = {
        "total_used_tokens": 0,
        "estimated_limit_tokens": None,
        "last_429_at": None,
        "last_error": None,
    }
    meta.meta["question_bank"] = {
        "path": str(QUESTION_BANK_PATH),
        "bank_version": bank_version,
        "total_questions": 0,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    meta.meta["content_factory"] = {
        "last_reset_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bank_version": bank_version,
        "reset_performed": True,
        "old_active_question_count": old_count,
        "deleted_question_count": old_count,
        "new_active_question_count": 0,
    }
    meta.meta["last_chapter_id"] = None
    meta.save()
    return {"old_active_question_count": old_count, "deleted_question_count": old_count, "new_active_question_count": 0}


def _replacement_candidates(config: RefillConfig) -> list[Dict[str, Any]]:
    rows = load_existing_items(QUESTION_BANK_PATH)
    candidates: list[Dict[str, Any]] = []
    for row in rows:
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        if row.get("bank_version") != config.bank_version or provenance.get("model") != config.model_name:
            candidates.append(row)
            continue
        quality = validate_generated_question(row, min_explanation_length=config.min_explanation_length)
        if not quality.is_valid:
            candidates.append(row)
    return candidates


def _drop_replaced_items(config: RefillConfig, replacement_count: int) -> int:
    if replacement_count <= 0:
        return 0
    candidates = _replacement_candidates(config)
    drop_ids = {str(row.get("id", "")) for row in candidates[:replacement_count]}
    if not drop_ids:
        return 0
    rows = [row for row in load_existing_items(QUESTION_BANK_PATH) if str(row.get("id", "")) not in drop_ids]
    _write_jsonl(QUESTION_BANK_PATH, rows)
    return len(drop_ids)


def run_refill(config: RefillConfig, meta_path: str = "bank/meta.json") -> RefillStats:
    load_dotenv()
    api_key = get_env("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    before_count = len(load_existing_items(QUESTION_BANK_PATH))
    reset_info = {"old_active_question_count": before_count, "deleted_question_count": 0, "new_active_question_count": before_count}
    reset_requested = config.reset_question_bank or config.mode == "reset_and_seed"
    if reset_requested:
        reset_info = reset_active_bank(meta_path=meta_path, bank_version=config.bank_version)
        before_count = 0

    meta = MetaManager(meta_path)
    meta.load()
    quota = meta.quota
    if config.hard_stop_on_near_quota and quota.is_near_limit(0.9):
        stats = RefillStats()
        stats.mode = config.mode
        stats.model_name = config.model_name
        stats.bank_version = config.bank_version
        stats.active_question_count_before = before_count
        stats.active_question_count_after = before_count
        return stats

    generator = GeminiQuestionGenerator(
        api_key=api_key,
        model_name=config.model_name,
        max_retry=config.max_retry,
        sleep_seconds=config.sleep_seconds_on_429,
    )
    allow_growth = config.mode in {"daily", "replace"}
    factory = ContentFactory(
        FactoryConfig(
            model_name=config.model_name,
            target_accepts=config.target_daily,
            min_explanation_length=config.min_explanation_length,
            max_attempts_per_target=config.max_retry,
            allow_over_floor_growth=allow_growth,
            bank_version=config.bank_version,
            mode=config.mode,
            max_runtime_minutes=config.max_runtime_minutes,
        ),
        generator,
    )
    stats = RefillStats.from_factory(factory.run(meta_path=meta_path), config=config)
    if config.mode == "replace":
        _drop_replaced_items(config, stats.accepted)
    stats.api_call_count = generator.api_call_count
    stats.rate_limit_errors = generator.rate_limit_errors
    stats.reset_performed = reset_requested
    stats.old_active_question_count = reset_info["old_active_question_count"]
    stats.deleted_question_count = reset_info["deleted_question_count"]
    stats.active_question_count_before = before_count
    stats.active_question_count_after = len(load_existing_items(QUESTION_BANK_PATH))
    return stats
