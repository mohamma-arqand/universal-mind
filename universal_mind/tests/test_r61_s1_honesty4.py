"""R61-S1 — the four honesty breaks, closed and pinned.

The deep review measured four sentences where the platform FABRICATED
instead of refusing or computing truly:

  «قیمت دلار الان چنده؟»      -> «نتیجه ۴»  (the 2+2 default leaked)
  «۲۰ درصد از ۵۰۰ چنده؟»      -> «نتیجه ۵۲۰» (percent translated to a SUM)
  «ساعت چنده؟»                -> «امروز ۲ دی، تاریخ ۱۴۰۵/۰۷/۱۰» (two calendars)
  «رگرسیون روی این اعداد»      -> silent training on DEFAULT_XS (fabricated data)
"""

from __future__ import annotations

from datetime import datetime

from universal_mind.persian_date import gregorian_to_jalali_parts
from universal_mind.persian_router import route_and_run


def _report(cmd: str) -> str:
    return str(route_and_run(cmd).get("agent_report", ""))


class TestHonestCompute:
    def test_a_knowledge_question_is_refused_not_answered_with_2p2(self) -> None:
        # R62 T2 evolution: «قیمت…» now gets the TOPIC-SPECIFIC refusal
        # (world-data needed, both roads offered) — still never «نتیجه ۴».
        rep = _report("قیمت دلار الان چنده؟")
        assert "نتیجه" not in rep
        assert "محاسبه‌ای نیست" in rep or "دادهٔ بیرونی" in rep

    def test_no_expression_means_no_default(self) -> None:
        # even the bare question shape with no numbers never evaluates 2+2
        rep = _report("حجم زمین چنده؟")
        assert "نتیجه" not in rep

    def test_real_arithmetic_still_works(self) -> None:
        rep = _report("۵ منهای ۳ چنده؟")
        assert "نتیجه ۲" in rep


class TestHonestPercent:
    def test_the_question_shape_computes_the_real_percent(self) -> None:
        rep = _report("۲۰ درصد از ۵۰۰ چنده؟")
        assert "برابر ۱۰۰" in rep
        assert "۵۲۰" not in rep

    def test_the_imperative_shape_too(self) -> None:
        assert "برابر ۱۰۰" in _report("درصد ۲۰ از ۵۰۰")

    def test_compute_is_never_in_a_percent_chain(self) -> None:
        p = route_and_run("۲۰ درصد از ۵۰۰ چنده؟")
        assert "compute" not in (p.get("route") or [])

    def test_the_result_is_named_as_a_percent(self) -> None:
        rep = _report("۲۰ درصد از ۵۰۰ چنده؟")
        assert "درصد محاسبه شد" in rep


class TestOneCalendar:
    def test_the_clock_answer_is_pure_jalali(self) -> None:
        rep = _report("ساعت چنده؟")
        now = datetime.now()
        _, jm, jd = gregorian_to_jalali_parts(now.year, now.month, now.day)
        months = {1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد",
                  6: "شهریور", 7: "مهر", 8: "آبان", 9: "آذر", 10: "دی",
                  11: "بهمن", 12: "اسفند"}
        # the Jalali day number AND month name must both appear
        fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        assert str(jd).translate(fa) in rep
        assert months[jm] in rep
        # and the GREGORIAN day number must not be glued to a Jalali month
        greg_day_wrong = f"{str(now.day).translate(fa)} {months[jm]}"
        assert greg_day_wrong not in rep


class TestHonestML:
    def test_no_data_is_refused_by_name(self) -> None:
        rep = _report("رگرسیون روی این اعداد")
        assert "داده‌ای در جمله پیدا نکردم" in rep
        assert "آموزش دید" not in rep

    def test_real_data_still_trains(self) -> None:
        rep = _report("رگرسیون روی ۱ و ۲ و ۳")
        assert "آموزش دید" in rep


class TestNoRegressionOfTheOldPaths:
    def test_stats_still_answer(self) -> None:
        rep = _report("میانگین ۳ و ۹ را حساب کن")
        assert "برابر ۶" in rep

    def test_unit_conversion_still_answers(self) -> None:
        rep = _report("۱۰ کیلومتر چند مایل است؟")
        assert "مایل" in rep
