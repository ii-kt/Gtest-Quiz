import pytest

from gtest_quiz import refill_pipeline
from gtest_quiz.content_factory import FactoryStats
from gtest_quiz.refill_pipeline import RefillConfig, RefillStats


def test_safe_parse_json_accepts_wrapped_model_text():
    data = refill_pipeline._safe_parse_json("prefix {\"question\":\"q\",\"correct_index\":1} suffix")
    assert data == {"question": "q", "correct_index": 1}


def test_refill_stats_wrap_factory_stats():
    factory_stats = FactoryStats(generated=3, accepted=2, queued_for_review=1, rejected=4, duplicates=5, errors=6)
    stats = RefillStats.from_factory(factory_stats)
    assert stats.generated == 3
    assert stats.accepted == 2
    assert stats.queued_for_review == 1
    assert stats.rejected == 4
    assert stats.duplicates == 5
    assert stats.errors == 6


def test_run_refill_stops_before_generation_when_quota_is_near(monkeypatch):
    class FakeQuota:
        def is_near_limit(self, ratio):
            assert ratio == 0.9
            return True

    class FakeMeta:
        quota = FakeQuota()

        def __init__(self, path):
            self.path = path

        def load(self):
            return None

    monkeypatch.setattr(refill_pipeline, "load_dotenv", lambda: None)
    monkeypatch.setattr(refill_pipeline, "get_env", lambda name: "test-key")
    monkeypatch.setattr(refill_pipeline, "MetaManager", FakeMeta)

    stats = refill_pipeline.run_refill(RefillConfig(target_daily=1))
    assert stats.generated == 0
    assert stats.accepted == 0


def test_run_refill_requires_api_key(monkeypatch):
    monkeypatch.setattr(refill_pipeline, "load_dotenv", lambda: None)
    monkeypatch.setattr(refill_pipeline, "get_env", lambda name: "")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        refill_pipeline.run_refill(RefillConfig(target_daily=1))
