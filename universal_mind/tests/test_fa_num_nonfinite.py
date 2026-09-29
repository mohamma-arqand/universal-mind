"""R52 regression: the Persian reporter must NAME non-finite numbers,
never crash on them.

The bomb: ``_fa_num`` did ``value == int(value)`` — ``int(nan)`` raises
ValueError and ``int(±inf)`` raises OverflowError. A REAL payload hits this:
``stats`` of a single-value series returns ``std=NaN`` (numpy), so the honest
report of «میانگین و انحراف یک عدد» crashed the whole Persian report — the
exact ``executes-but-wrong`` family (R49's ``_fa_num(rows)`` crash was the
same function, different hole).

The law now: NaN renders as «نامشخص», ±inf as «بی‌نهایت», and the report
narrates a non-finite std without dying.
"""

from __future__ import annotations

from universal_mind.persian_report import _fa_num, persian_report


class TestFaNumNonFinite:
    """Non-finite floats are named in Persian, never raised."""

    def test_nan_is_named_not_crashed(self) -> None:
        assert _fa_num(float("nan")) == "نامشخص"

    def test_positive_infinity_is_named(self) -> None:
        assert _fa_num(float("inf")) == "بی‌نهایت"

    def test_negative_infinity_is_named(self) -> None:
        assert _fa_num(float("-inf")) == "بی‌نهایت"

    def test_normal_numbers_still_render(self) -> None:
        assert _fa_num(3.266) == "۳.۲۶۶"
        assert _fa_num("12") == "۱۲"
        assert _fa_num(42) == "۴۲"

    def test_a_non_numeric_label_still_renders_as_is(self) -> None:
        assert _fa_num("میانگین") == "میانگین"


class TestReportSurvivesNonFinite:
    """A REAL single-value stats payload (std=NaN) narrates honestly."""

    def test_a_single_value_stats_report_does_not_crash(self) -> None:
        # numpy's std of one value is NaN — the honest live payload:
        payload = {
            "ok": True,
            "command": "میانگین و انحراف عدد ۵ را بگو",
            "route": ["data"],
            "result": {
                "data": {
                    "ok": True,
                    "mean": 5.0,
                    "std": float("nan"),
                    "min": 5.0,
                    "max": 5.0,
                }
            },
            "extracted_params": {"data": {}},
        }
        text = str(persian_report(payload))
        # the report LIVES and names the unknowable spread:
        assert "نامشخص" in text

    def test_an_infinite_accuracy_is_named_not_crashed(self) -> None:
        payload = {
            "ok": True,
            "command": "دقت مدل",
            "route": ["ai"],
            "result": {"ai": {"ok": True, "accuracy": float("inf")}},
            "extracted_params": {"ai": {}},
        }
        text = str(persian_report(payload))
        assert "بی‌نهایت" in text
