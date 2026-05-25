import pytest

from gtest_quiz.question_quality import validate_generated_question


def test_valid_question():
    data = {
        "question": "ニューラルネットワークにおける活性化関数の役割は何か。",
        "choices": [
            "線形性を維持する",
            "非線形性を導入する",
            "計算量を削減する",
            "重みを初期化する",
        ],
        "correct_index": 1,
        "explanation": (
            "正解理由: 活性化関数は非線形性を導入し、ニューラルネットワークが複雑な関係を学習できるようにするため重要である。"
            "不正解理由: 線形性維持、計算量削減、重み初期化は活性化関数の中心的な役割ではなく、設問の概念との差分が明確である。"
        ),
        "difficulty": "standard",
    }

    result = validate_generated_question(data)
    assert result.is_valid


def test_invalid_short_explanation():
    data = {
        "question": "AIとは何か。",
        "choices": ["A", "B", "C", "D"],
        "correct_index": 0,
        "explanation": "短い",
        "difficulty": "basic",
    }

    result = validate_generated_question(data)
    assert not result.is_valid
