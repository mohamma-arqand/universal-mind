"""R62 T1 — appointments: the weekday sentence, the trailing marker, the view.

The sweep measured: «جلسه شنبه ساعت ۱۰ است — یادت باشد» → «نشناختم» (the
marker trails the fact; the reminder gate never saw «یادت باشد»), and
«قرارهایم را نشان بده» → dead (the agenda knew «برنامه‌ام» but not «قرار»).

All distance checks are DYNAMIC (compared to an independent weekday
computation) — the R60 lesson: never pin today's answer; today moves.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from universal_mind.persian_router import route_and_run
from universal_mind.scheduler import parse_one_shot


@pytest.fixture()
def probe_appointment():
    route_and_run("جلسه شنبه ساعت ۱۰ است — یادت باشد")
    yield
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%جلسه شنبه%'")


class TestWeekdayMoments:
    def test_all_seven_days_match_the_independent_distance(self) -> None:
        table = {"شنبه": 5, "یکشنبه": 6, "دوشنبه": 0, "سه‌شنبه": 1,
                 "چهارشنبه": 2, "پنجشنبه": 3, "جمعه": 4}
        for word, py in table.items():
            parsed = parse_one_shot(f"جلسه {word} ساعت ۱۰ است")
            assert parsed is not None, word
            real = next(d for d in range(8)
                        if (datetime.now() + timedelta(days=d)).weekday() == py)
            assert parsed["day_offset"] == real, (word, parsed, real)

    def test_next_week_forces_the_next_cycle(self) -> None:
        parsed = parse_one_shot("جلسه شنبه آینده ساعت ۱۰ است")
        real = next(d for d in range(1, 15)
                    if (datetime.now() + timedelta(days=d)).weekday() == 5)
        assert parsed is not None and parsed["day_offset"] == real


class TestTheTrailingMarker:
    def test_the_appointment_registers_as_a_reminder(self, probe_appointment) -> None:
        p = route_and_run("جلسه شنبه ساعت ۱۰ است — یادت باشد")
        assert p.get("ok") is True
        assert "ثبت شد" in p["agent_report"]

    def test_the_reminder_text_does_not_carry_the_marker(self, probe_appointment) -> None:
        p = route_and_run("جلسه شنبه ساعت ۱۰ است — یادت باشد")
        rep = p["agent_report"]
        inner = rep.split("«")[1].split("»")[0] if "«" in rep else ""
        assert "یادت باشد" not in inner
        assert "جلسه" in inner

    def test_a_pure_fact_stays_a_fact(self) -> None:
        p = route_and_run("یادت باشد که من قهوه تلخ دوست دارم")
        assert p.get("ok") is True and "یادداشت شد" in p["agent_report"]
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite(persistent=True)
        db.execute("DELETE FROM named_memory WHERE fact LIKE '%قهوه تلخ%'")


class TestTheAppointmentsView:
    def test_gharar_joins_the_agenda_words(self, probe_appointment) -> None:
        p = route_and_run("قرارهایم را نشان بده")
        assert p.get("ok") is True
        assert "جلسه شنبه" in p["agent_report"]

    def test_the_plain_fact_is_not_left_in_the_list(self) -> None:
        # the fact-store must NOT hold the appointment (it is a reminder now)
        from universal_mind.database_suite import DatabaseSuite

        db = DatabaseSuite(persistent=True)
        q = db.query("SELECT COUNT(*) n FROM named_memory WHERE fact LIKE '%جلسه شنبه%'")
        n = q["rows"][0]["n"] if q.get("ok") else 0
        assert n == 0
