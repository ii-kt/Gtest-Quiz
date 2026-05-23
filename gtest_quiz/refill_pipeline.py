"""Content refill pipeline backed by the schema-first content factory."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel

from gtest_quiz.content_factory import ContentFactory, FactoryConfig, FactoryStats, GeneratedQuestionSpec
from gtest_quiz.env import get_env, load_dotenv
from gtest_quiz.meta import MetaManager
<<<<<<< ours
=======
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank
from gtest_quiz.question_quality import (
    build_duplicate_index,
    is_probable_duplicate,
    validate_generated_question,
)
from gtest_quiz.env import get_env, load_dotenv
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


class RefillConfig:
    def __init__(
        self,
        *,
        model_name: str = "gemini-2.5-flash-lite",
        target_daily: int = 80,
        max_retry: int = 3,
        min_explanation_length: int = 80,
        sleep_seconds_on_429: float = 2.0,
        hard_stop_on_near_quota: bool = True,
    ) -> None:
        self.model_name = model_name
        self.target_daily = target_daily
        self.max_retry = max_retry
        self.min_explanation_length = min_explanation_length
        self.sleep_seconds_on_429 = sleep_seconds_on_429
        self.hard_stop_on_near_quota = hard_stop_on_near_quota


class RefillStats:
    def __init__(self) -> None:
        self.generated = 0
        self.accepted = 0
        self.rejected = 0
        self.duplicates = 0
        self.errors = 0
        self.queued_for_review = 0

    @classmethod
    def from_factory(cls, stats: FactoryStats) -> "RefillStats":
        item = cls()
        item.generated = stats.generated
        item.accepted = stats.accepted
        item.rejected = stats.rejected
        item.duplicates = stats.duplicates
        item.errors = stats.errors
        item.queued_for_review = stats.queued_for_review
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
            time.sleep(self.sleep_seconds)
        if last_error:
            raise last_error
        raise RuntimeError("Gemini did not return a structured question")

    def _generate_once(self, prompt: str, schema: type[BaseModel]) -> Optional[Dict[str, Any]]:
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


def run_refill(config: RefillConfig, meta_path: str = "bank/meta.json") -> RefillStats:
    load_dotenv()
    api_key = get_env("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    meta = MetaManager(meta_path)
    meta.load()
    quota = meta.quota
    if config.hard_stop_on_near_quota and quota.is_near_limit(0.9):
        return RefillStats()

    generator = GeminiQuestionGenerator(
        api_key=api_key,
        model_name=config.model_name,
        max_retry=config.max_retry,
        sleep_seconds=config.sleep_seconds_on_429,
    )
    factory = ContentFactory(
        FactoryConfig(
            model_name=config.model_name,
            target_accepts=config.target_daily,
            min_explanation_length=config.min_explanation_length,
        ),
        generator,
    )
    return RefillStats.from_factory(factory.run(meta_path=meta_path))
