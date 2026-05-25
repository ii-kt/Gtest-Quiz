from tools.benchmark_learning_policy import run_policy_benchmark
from tests.bank_fixture import install_temp_question_bank


def test_learning_policy_benchmark_reaches_expected_coverage(tmp_path, monkeypatch):
    install_temp_question_bank(monkeypatch, tmp_path)
    result = run_policy_benchmark(seed=3, rounds=80)
    assert result["policy"] == "adaptive_mastery_v2"
    assert result["rounds"] == 80
    assert result["unique_questions"] >= 40
    assert result["covered_chapters"] >= 10
    assert result["scheduled_items"] >= 40
