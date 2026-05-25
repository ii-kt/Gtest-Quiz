from backend.app.experiments import ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY, RANDOM_POLICY
from tools.benchmark_learning_policy import compare_policy_benchmarks, run_policy_benchmark
from tests.bank_fixture import install_temp_question_bank


def test_policy_benchmark_supports_all_variants(tmp_path, monkeypatch):
    install_temp_question_bank(monkeypatch, tmp_path)
    for policy in [ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY, RANDOM_POLICY]:
        result = run_policy_benchmark(seed=5, rounds=40, policy_variant=policy)
        assert result["policy"] == policy
        assert result["rounds"] == 40
        assert result["scheduled_items"] >= 20


def test_policy_comparison_reports_recommended_adaptive_policy(tmp_path, monkeypatch):
    install_temp_question_bank(monkeypatch, tmp_path)
    comparison = compare_policy_benchmarks(seed=6, rounds=60)
    assert comparison["recommended_policy"] == ADAPTIVE_POLICY
    assert set(comparison["results"]) == {ADAPTIVE_POLICY, CHAPTER_BALANCED_POLICY, RANDOM_POLICY}
    assert "adaptive_vs_random_scheduled" in comparison["deltas"]
