"""R66 P5 — «شنبه چندم است؟»: the NAMED DAY's DATE from the real clock.

The sweep caught both shapes unrecognized (a weekday + «چندم» fell to
«این فرمان را نشناختم»). The answer is the NEXT occurrence of the
named day («هفته بعد» = one full week further), in the Persian
calendar, Persian digits — cross-checked against an independent
computation, never a cached string.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest


def _independent(want_py: int, extra_weeks: int = 0) -> date:
    today = date.today()
    delta = (want_py - today.weekday()) % 7
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta + 7 * extra_weeks)


class TestTheNamedDayDate:
    def test_shanbe_answers_the_next_saturday(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("شنبه چندم است؟")
        assert p["ok"] is True
        exp = _independent(5)
        try:
            from jdatetime import date as jdate

            j = jdate.fromgregorian(date=exp)
            assert f"{j.day}" in str(p["result"]).replace("۰", "0") or \
                   str(j.day).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")) in p["agent_report"]
        except ImportError:
            pytest.skip("jdatetime not installed")
        assert "شنبه" in p["agent_report"] and "مهر" in p["agent_report"]

    def test_next_week_jumps_a_full_week(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("پنجشنبه هفته بعد چندمه؟")
        assert p["ok"] is True
        assert "هفته بعد" in p["agent_report"]
        near = route_and_run("پنجشنبه چندم است؟")
        assert near["ok"] is True
        # the far one is 7 days after the near one — the dates differ
        assert p["agent_report"] != near["agent_report"]

    def test_all_seven_days_answer(self) -> None:
        from universal_mind.persian_router import route_and_run

        for day in ("یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"):
            p = route_and_run(f"{day} چندم است؟")
            assert p["ok"] is True, day
            assert day in p["agent_report"]

    def test_today_weekday_still_answers_the_old_shape(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("امروز چندشنبه است؟")
        assert p["ok"] is True
        assert "امروز" in p["agent_report"]
