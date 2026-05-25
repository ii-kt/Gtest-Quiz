from __future__ import annotations

import json
from pathlib import Path


def install_temp_question_bank(monkeypatch, tmp_path: Path, count: int = 60) -> Path:
    bank_path = tmp_path / "question_bank.jsonl"
    rows = []
    for index in range(count):
        chapter_index = (index % 15) + 1
        rows.append(
            {
                "id": f"TEST_G35_{index:04d}",
                "source": "gemini35_content_factory",
                "created_at": "2026-05-26T00:00:00Z",
                "bank_version": "gemini35_v1",
                "domain": "技術分野",
                "chapter_group": "テスト用章",
                "chapter_id": f"{chapter_index}. テスト用項目",
                "difficulty": ["basic", "standard", "advanced"][index % 3],
                "question": f"G検定の概念理解を確認するテスト問題 {index} として最も適切なものはどれか。",
                "choices": [
                    "正しい概念の関係を説明している",
                    "単なる暗記だけを求めている",
                    "誤った因果関係を前提にしている",
                    "対象外の制度だけを説明している",
                ],
                "correct_index": 0,
                "explanation": (
                    "正解理由: この選択肢は概念同士の関係を正しく説明しており、G検定で問われる理解に合っている。"
                    "不正解理由: 他の選択肢は単純暗記、誤った因果、対象外の制度に寄っており、設問の中心概念との差分が明確である。"
                ),
                "syllabus": "G2024_v1.3",
                "provenance": {
                    "model": "gemini-3.5-flash",
                    "prompt_version": "test_fixture",
                    "generated_at": "2026-05-26T00:00:00Z",
                    "validator_score": 100,
                    "validator_reasons": [],
                    "syllabus_node": f"{chapter_index}. テスト用項目",
                    "concepts": ["fixture"],
                    "bank_version": "gemini35_v1",
                },
            }
        )
    bank_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")

    import gtest_quiz.question_bank as qb

    monkeypatch.setattr(qb, "BANK_PATH", bank_path)
    monkeypatch.setattr(qb, "_IS_LOADED", False)
    monkeypatch.setattr(qb, "_QUESTION_CACHE", {})
    return bank_path
