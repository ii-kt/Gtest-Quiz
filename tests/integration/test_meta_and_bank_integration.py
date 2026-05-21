import json
from pathlib import Path

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import Question
from gtest_quiz.question_bank import load_question_bank


def test_meta_tracks_usage_and_quota(tmp_path: Path):
    meta_path = tmp_path / "meta.json"
    m = MetaManager(str(meta_path))
    m.load()

    m.record_usage("1. 人工知能の定義", "offline")
    m.record_usage("1. 人工知能の定義", "online")

    q = m.get_quota_manager()
    q.add_usage(1200)
    q.register_429("quota exceeded")

    m.save()

    saved = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved["usage"]["total_questions"] == 2
    assert saved["usage"]["online_questions"] == 1
    assert saved["usage"]["offline_questions"] == 1
    assert saved["quota_estimate"]["total_used_tokens"] >= 1200
    assert saved["quota_estimate"]["estimated_limit_tokens"] is not None


def test_question_bank_loads_from_temp_file(tmp_path: Path, monkeypatch):
    bank_path = tmp_path / "question_bank.jsonl"
    q = Question(
        id="Q_TEST_001",
        source="test",
        created_at="2026-01-01T00:00:00Z",
        domain="技術分野",
        chapter_group="人工知能とは",
        chapter_id="1. 人工知能の定義",
        difficulty="basic",
        question="AIの定義として適切なものはどれか。",
        choices=["A", "B", "C", "D"],
        correct_index=0,
        explanation="説明文は最低限の長さを満たすために十分な文章量を含めています。",
        syllabus="G2024_v1.3",
    )
    bank_path.write_text(json.dumps(q.to_dict(), ensure_ascii=False) + "\n", encoding="utf-8")

    import gtest_quiz.question_bank as qb

    monkeypatch.setattr(qb, "BANK_PATH", bank_path)
    monkeypatch.setattr(qb, "_IS_LOADED", False)
    monkeypatch.setattr(qb, "_QUESTION_CACHE", {})

    loaded = load_question_bank(force_reload=True)
    assert "Q_TEST_001" in loaded
