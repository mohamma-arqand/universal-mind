"""R60 Q3 — time-until and weekday-distance, real and honest.

«چند دقیقه تا نیمه‌شب مانده؟» and «شنبه چند روز دیگه است؟» both returned
«نشناختم». The clock is REAL (datetime.now) and every digit is Persian.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from universal_mind.reflexive import answer_reflexive


def _fa_num(value: int | float | str) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


class TestTimeUntil:
    def test_midnight_answered_from_the_real_clock(self) -> None:
        ans = answer_reflexive("چند دقیقه تا نیمه‌شب مانده؟")
        assert ans is not None
        rep = ans["agent_report"]
        now = datetime.now()
        mid = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        mins = int((mid - now).total_seconds() // 60)
        h, m = divmod(mins, 60)
        assert _fa_num(h) in rep and _fa_num(m) in rep and "نیمه‌شب" in rep

    def test_next_hour_answered(self) -> None:
        ans = answer_reflexive("چند دقیقه تا ساعت بعدی مانده؟")
        assert ans is not None
        assert "دقیقه" in ans["agent_report"]

    def test_no_negative_or_zero_minutes(self) -> None:
        ans = answer_reflexive("چند دقیقه تا نیمه‌شب مانده؟")
        rep = ans["agent_report"]
        assert "۰ دقیقه" not in rep  # midnight is at least a minute away


class TestWeekdayDistance:
    def test_all_seven_days_match_the_independent_calculation(self) -> None:
        pairs = [("شنبه", 5), ("یکشنبه", 6), ("دوشنبه", 0), ("سه‌شنبه", 1),
                 ("چهارشنبه", 2), ("پنجشنبه", 3), ("جمعه", 4)]
        for name, py_wd in pairs:
            ans = answer_reflexive(f"{name} چند روز دیگه است؟")
            assert ans is not None, name
            rep = ans["agent_report"]
            expected = (py_wd - datetime.now().weekday()) % 7
            if expected == 0:
                assert "امروز است" in rep, (name, rep)
            else:
                assert f"{_fa_num(expected)} روز" in rep, (name, rep, expected)

    def test_the_substring_law_doshanbe_is_not_shanbe(self) -> None:
        # «شنبه» is a substring of «دوشنبه» — the longest match must win
        ans = answer_reflexive("دوشنبه چند روز دیگه است؟")
        assert ans is not None
        rep = ans["agent_report"]
        expected = (0 - datetime.now().weekday()) % 7
        assert rep.startswith("تا دوشنبه") or "دوشنبه امروز است" in rep
        assert _fa_num(expected) in rep

    def test_the_spelled_without_zwnj_shape_works(self) -> None:
        ans = answer_reflexive("سهشنبه چند روز دیگه است؟")
        assert ans is not None
        rep = ans["agent_report"]
        expected = (1 - datetime.now().weekday()) % 7
        assert f"{_fa_num(expected)} روز" in rep or "امروز است" in rep
