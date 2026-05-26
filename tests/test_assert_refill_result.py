from tools.assert_refill_result import assert_refill_result


def test_assert_refill_result_fails_reset_without_accepts():
    errors = assert_refill_result({"mode": "reset_and_seed", "accepted": 0, "errors": 0})
    assert "reset_and_seed requires accepted >= 1" in errors


def test_assert_refill_result_allows_daily_quota_stop():
    errors = assert_refill_result({"mode": "daily", "accepted": 0, "errors": 0, "rate_limit_errors": 1})
    assert errors == []


def test_assert_refill_result_fails_errors_without_accepts():
    errors = assert_refill_result({"mode": "daily", "accepted": 0, "errors": 1, "rate_limit_errors": 1})
    assert "errors > 0 and accepted == 0" in errors
