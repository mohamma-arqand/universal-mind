"""R71 P1-P6 — comparisons, text transforms, reminder-text editing,
N-days-later dates, line-by-line reads, word frequency.

Two LIVE wrong answers from the sweep:
- «این جمله را برعکس کن: سلام دنیا» routed to IMAGE processing (a PNG
  was inspected!) — a text transform stole by the flip word.
- «متن یادآوری X را عوض کن به Y» fell to the file move with an empty
  destination («مقصد '' از قبل هست»).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest


@pytest.fixture()
def probe_file(tmp_path: Path) -> Path:
    f = tmp_path / "gwr71.txt"
    f.write_text("خط اول\nخط دوم\nخط سوم گواه\nخط چهارم", encoding="utf-8")
    return f


class TestCompare:
    def test_greater_answers_true(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۵ بزرگتر از ۳ است؟")
        assert p["ok"] is True
        assert p["route"] == ["data"]  # never llm
        assert "بزرگتر است از ۳" in p["agent_report"]

    def test_less_answers_true(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۲ کوچکتر از ۹ است؟")
        assert p["ok"] is True
        assert "کوچکتر است از" in p["agent_report"]


class TestReverseText:
    def test_a_text_transform_never_routes_to_image(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("این جمله را برعکس کن: سلام دنیا")
        assert p["ok"] is True
        assert "image" not in p["route"]
        assert "ایند مالس" in p["agent_report"]  # «سلام دنیا» reversed


class TestReminderTextEdit:
    def test_the_text_really_changes_in_the_db(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run
        from universal_mind.scheduler import (
            delete_schedule,
            list_schedules,
            register_one_shot,
        )

        DatabaseSuite(persistent=True).execute(
            "DELETE FROM schedules WHERE command LIKE '%گواه-r71-t%'")
        register_one_shot("فردا ساعت ۹ گواه-r71-t")
        try:
            p = route_and_run("متن یادآور گواه-r71-t را عوض کن به جلسهی مهم گواه-r71-t")
            assert p["ok"] is True
            assert p["route"] == ["scheduler"]  # never textfile/move
            row = next(s for s in list_schedules()
                       if "گواه-r71-t" in s.command)
            assert "جلسهی مهم" in row.command       # the DB row changed
            assert "عوض شد" in p["agent_report"]
            assert "جلسهی مهم" in p["agent_report"]  # both sides named
        finally:
            for s in list_schedules():
                if "گواه-r71-t" in s.command:
                    delete_schedule(s.schedule_id)

    def test_an_unknown_text_refuses(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("متن یادآور ناموجود-zz71 را عوض کن به چیز")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]


class TestNDaysLater:
    def test_matches_the_independent_computation(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۲۰ روز دیگر چندمه؟")
        tgt = date.today() + timedelta(days=20)
        from jdatetime import date as jdate

        j = jdate.fromgregorian(date=tgt)
        _fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        assert p["ok"] is True
        assert str(j.day).translate(_fa) in p["agent_report"]


class TestLineReads:
    def test_the_third_line(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"خط سوم فایل {probe_file} را نشان بده")
        assert p["ok"] is True
        assert "خط ۳ از ۴" in p["agent_report"]
        assert "خط سوم گواه" in p["agent_report"]

    def test_the_last_line_is_a_read_never_speech(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"آخرین خط فایل {probe_file} را بگو")
        assert p["ok"] is True
        assert p["route"] == ["textfile"]  # the «بگو» word did not chain speech
        assert "خط چهارم" in p["agent_report"]

    def test_out_of_range_is_an_honest_refusal(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"خط نهم فایل {probe_file} را نشان بده")
        assert p["ok"] is False
        assert "نیست" in p["agent_report"]


class TestWordFrequency:
    def test_the_real_count(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"کلمه گواه در فایل {probe_file} چند بار آمده؟")
        assert p["ok"] is True
        assert "۱ بار" in p["agent_report"]

    def test_an_absent_word_says_so(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"کلمه فلان-نیست در فایل {probe_file} چند بار آمده؟")
        assert p["ok"] is True
        assert "نیامده است" in p["agent_report"]
