"""R58 M2 — relative dates: «فردا چندمه؟» and friends, answered for real.

Measured gap (the 18-command sweep): «فردا چندمه؟» returned «نشناختم» — the
reflexive gate only knew «امروز». jalali_date(offset_days) already existed;
the gate just never recognized the relative words.
"""

from __future__ import annotations

from universal_mind.persian_date import jalali_date
from universal_mind.reflexive import answer_reflexive


class TestRelativeDates:
    def test_tomorrow(self) -> None:
        out = answer_reflexive("فردا چندمه؟")
        assert out is not None and f"فردا {jalali_date(1)}" in out["agent_report"]

    def test_yesterday(self) -> None:
        out = answer_reflexive("دیروز چه روزی بود؟")
        assert out is not None and f"دیروز {jalali_date(-1)}" in out["agent_report"]

    def test_day_after_tomorrow_with_zwnj(self) -> None:
        out = answer_reflexive("پس‌فردا چندمه؟")
        # the LONGEST match wins: «پس‌فردا» contains «فردا», and the first
        # draft answered "فردا" for it — a live witness caught that.
        assert out is not None and f"پس‌فردا {jalali_date(2)}" in out["agent_report"]

    def test_day_after_tomorrow_glued(self) -> None:
        out = answer_reflexive("پسفردا چندمه؟")
        assert out is not None and f"پسفردا {jalali_date(2)}" in out["agent_report"]

    def test_day_before_yesterday(self) -> None:
        out = answer_reflexive("پریروز چندمه؟")
        assert out is not None and f"پریروز {jalali_date(-2)}" in out["agent_report"]

    def test_today_is_untouched(self) -> None:
        out = answer_reflexive("امروز چندمه؟")
        assert out is not None and f"امروز {jalali_date(0)}" in out["agent_report"]

    def test_past_days_say_bud_future_say_ast(self) -> None:
        past = answer_reflexive("دیروز چندمه؟")["agent_report"]
        future = answer_reflexive("فردا چندمه؟")["agent_report"]
        assert "بود" in past and "است" in future

    def test_a_plain_statement_about_tomorrow_is_not_a_date_question(self) -> None:
        # «فردا گزارش می‌دهم» mentions tomorrow but asks no date — must not
        # be hijacked into a calendar answer.
        out = answer_reflexive("فردا گزارش می‌دهم")
        assert out is None or "۱۴۰۵" not in out["agent_report"].split("گزارش")[0]

    def test_the_answer_uses_persian_digits(self) -> None:
        import re

        rep = answer_reflexive("فردا چندمه؟")["agent_report"]
        assert not re.search(r"[0-9]", rep)
