import json
from pathlib import Path

from gtest_quiz.content_factory import (
    ContentFactory,
    CoverageTarget,
    FactoryConfig,
    GeneratedQuestionSpec,
    build_coverage_targets,
    decide_candidate,
)
from gtest_quiz.meta import MetaManager
from gtest_quiz.question_quality import build_duplicate_index
from tools.review_generated_queue import summarize_queue


class StaticGenerator:
    def __init__(self) -> None:
        self.count = 0

    def generate(self, prompt: str, schema: type[GeneratedQuestionSpec]):
        self.count += 1
        return {
            "question": f"汎化性能を確認する目的として最も適切なものはどれか。{self.count}",
            "choices": [
                "未知データに対する性能を見積もるため",
                "訓練データを暗号化するため",
                "モデルの重みを固定するため",
                "入力データを削除するため",
            ],
            "correct_index": 0,
            "explanation": "汎化性能は未知データに対する性能を示すため、訓練データだけでは見えない過学習を検出するうえで重要である。",
            "difficulty": "standard",
            "syllabus_node": "10. モデルの選択・評価",
            "concepts": ["汎化性能", "評価"],
            "source_hint": "test",
        }


def test_decide_candidate_routes_duplicates():
    data = {
        "question": "ニューラルネットワークにおける活性化関数の役割は何か。",
        "choices": ["線形性を維持する", "非線形性を導入する", "計算量を削減する", "重みを初期化する"],
        "correct_index": 1,
        "explanation": "活性化関数は非線形性を導入し、モデルが複雑な関係を学習できるようにするために重要である。",
        "difficulty": "standard",
    }
    duplicate_index = build_duplicate_index([data])
    decision = decide_candidate(data, duplicate_index=duplicate_index, min_explanation_length=40, review_threshold=75)
    assert decision.action == "duplicate"


def test_coverage_targets_prioritize_deficits(tmp_path: Path):
    meta_path = tmp_path / "meta.json"
    meta = MetaManager(str(meta_path))
    meta.load()
    meta.meta["chapters"] = {
        "g": {
            "label": "group",
            "subchapters": {
                "a": {"label": "A", "weight": 1.0},
                "b": {"label": "B", "weight": 1.0},
            },
        }
    }
    targets = build_coverage_targets(meta, [{"chapter_id": "A"}, {"chapter_id": "A"}], per_chapter_floor=3)
    assert targets[0].chapter_id == "B"
    assert targets[0].priority > targets[1].priority


def test_content_factory_accepts_and_writes_provenance(tmp_path: Path):
    bank = tmp_path / "question_bank.jsonl"
    review = tmp_path / "review.jsonl"
    provenance = tmp_path / "provenance.jsonl"
    meta_path = tmp_path / "meta.json"
    meta = MetaManager(str(meta_path))
    meta.load()
    meta.meta["chapters"] = {
        "g": {
            "label": "機械学習の概要",
            "subchapters": {"m": {"label": "10. モデルの選択・評価", "weight": 1.0}},
        }
    }
    meta.save()

    factory = ContentFactory(
        FactoryConfig(
            target_accepts=1,
            question_bank_path=bank,
            review_queue_path=review,
            provenance_path=provenance,
            min_explanation_length=40,
        ),
        StaticGenerator(),
    )
    stats = factory.run(meta_path=str(meta_path))
    assert stats.accepted == 1
    written = json.loads(bank.read_text(encoding="utf-8").splitlines()[0])
    assert written["provenance"]["prompt_version"]
    assert written["provenance"]["validator_score"] >= 75
    assert provenance.exists()


def test_review_queue_summary(tmp_path: Path):
    queue = tmp_path / "review.jsonl"
    queue.write_text(
        "\n".join(
            [
                json.dumps({"decision": "review"}, ensure_ascii=False),
                json.dumps({"decision": "reject"}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    summary = summarize_queue(queue)
    assert summary == {"total": 2, "by_decision": {"reject": 1, "review": 1}}
