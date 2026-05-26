from tools.release_readiness import evaluate_release_readiness


def test_release_readiness_static_gates_are_green():
    result = evaluate_release_readiness(profile="bootstrap")
    failed = [check["name"] for check in result["checks"] if not check["passed"]]
    assert failed == []
