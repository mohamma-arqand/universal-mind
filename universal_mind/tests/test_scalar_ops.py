"""Tests: real scalar arithmetic — the operator gets the RESULT, not stats."""

from __future__ import annotations


class TestScalarOps:
    def test_multiply_is_real(self) -> None:
        """«ضرب ۳ در ۴» → 12, never the stats of [3,4]."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("ضرب ۳ در ۴ را حساب کن")
        assert payload["ok"] is True
        assert payload["result"]["data"]["result"] == 12.0

    def test_sqrt_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("جذر ۱۶ را حساب کن")
        assert payload["result"]["data"]["result"] == 4.0

    def test_percent_is_real(self) -> None:
        """«درصد ۲۵ از ۸۰» → 20 (25% OF 80)."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("درصد ۲۵ از ۸۰")
        assert payload["result"]["data"]["result"] == 20.0

    def test_power_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("توان ۲ به ۱۰")
        assert payload["result"]["data"]["result"] == 1024.0

    def test_divide_is_real(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("تقسیم ۱۰ بر ۴")
        assert payload["result"]["data"]["result"] == 2.5

    def test_divide_by_zero_is_honest(self) -> None:
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("تقسیم ۵ بر ۰")
        assert payload["ok"] is False
        assert "صفر" in str((payload.get("errors") or {}).get("data", ""))

    def test_plain_stats_still_work(self) -> None:
        """«میانگین ۳ و ۹» keeps its stats operation — no hijack."""
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("میانگین ۳ و ۹ را حساب کن")
        assert payload["extracted_params"]["data"]["operation"] == "stats"