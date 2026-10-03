"""R70 P1-P6 — conversion ownership, word count, day-scoped appointments,
the week's plan, the honest unfinished list, and real primes.

The sweep's findings:
- «۵ کیلوگرم چند پوند است؟» chained unitconvert ← sysstatus (an
  irrelevant vitals step on a one-question sentence).
- «در فایل X چند کلمه هست؟» was unrecognized.
- «فردا چند تا قرار دارم؟» answered the blanket reminder TOTAL.
- «برنامه این هفته‌ام» and «چه کارهای ناتمامی دارم؟» were unrecognized.
- «بین ۱۰ و ۲۰ چند عدد اول هست؟» was unrecognized (a data question
  with the range IN the sentence).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def probe_file(tmp_path: Path) -> Path:
    f = tmp_path / "gwr70.txt"
    f.write_text("سلام دنیا این یک فایل گواه است", encoding="utf-8")
    return f


@pytest.fixture()
def tomorrow_appt():
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.scheduler import delete_schedule, register_one_shot

    DatabaseSuite(persistent=True).execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r70-t%'")
    register_one_shot("فردا ساعت ۱۰ جلسه گواه-r70-t")
    yield
    from universal_mind.scheduler import list_schedules

    for s in list_schedules():
        if "گواه-r70-t" in s.command:
            delete_schedule(s.schedule_id)


class TestConversionOwnership:
    def test_a_conversion_never_chains_status(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۵ کیلوگرم چند پوند است؟")
        assert p["ok"] is True
        assert p["route"] == ["unitconvert"]  # sysstatus stepped aside

    def test_the_conversion_answers_the_real_number(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("۱۰۰ درجه فارنهایت چند سانتیگراد است؟")
        assert p["ok"] is True
        assert "۳۷" in p["agent_report"]  # 100F = 37.8C, Persian digits


class TestWordCount:
    def test_the_real_word_count(self, probe_file: Path) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run(f"در فایل {probe_file} چند کلمه هست؟")
        assert p["ok"] is True
        assert "۷ کلمه" in p["agent_report"]
        assert "۱ سطر" in p["agent_report"]

    def test_a_missing_file_refuses(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("در فایل D:/um_missing_zz.txt چند کلمه هست؟")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]


class TestDayScopedAppointments:
    def test_tomorrows_count_with_names(self, tomorrow_appt) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("فردا چند تا قرار دارم؟")
        assert p["ok"] is True
        assert "فردا ۱ قرار داری" in p["agent_report"]
        assert "جلسه گواه-r70-t" in p["agent_report"]  # the row is NAMED

    def test_pas_farda_is_its_own_day(self, tomorrow_appt) -> None:
        from universal_mind.persian_router import route_and_run

        # THE SUBSTRING LAW: «پس‌فردا» contains «فردا» — the longer word
        # must win or the empty day lists tomorrow's row.
        p = route_and_run("پس‌فردا چند تا قرار دارم؟")
        assert p["ok"] is True
        assert "هیچ قرار" in p["agent_report"]
        assert "جلسه" not in p["agent_report"]

    def test_the_blanket_count_still_works(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند تا یادآور داری؟")
        assert p["ok"] is True
        assert "یادآور" in p["agent_report"]


class TestTheWeeksPlan:
    def test_the_week_lists_the_real_rows(self, tomorrow_appt) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("برنامه این هفته‌ام را نشان بده")
        assert p["ok"] is True
        assert "برنامهٔ این هفته" in p["agent_report"]
        assert "جلسه گواه-r70-t" in p["agent_report"]


class TestTheUnfinishedList:
    def test_a_done_goal_is_not_unfinished(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چه کارهای ناتمامی دارم؟")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "ناتمام" in rep
        assert "— done" not in rep  # finished goals never appear


class TestPrimes:
    def test_the_real_primes_in_range(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("بین ۱۰ و ۲۰ چند عدد اول هست؟")
        assert p["ok"] is True
        assert p["route"] == ["data"]
        assert "۴ عدد اول" in p["agent_report"]
        assert "۱۱، ۱۳، ۱۷، ۱۹" in p["agent_report"]

    def test_a_prime_free_range_says_so(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("بین ۲۴ و ۲۸ چند عدد اول هست؟")
        assert p["ok"] is True
        assert "هیچ عدد اولی" in p["agent_report"]
