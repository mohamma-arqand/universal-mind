"""R65 P2 — «هر ۳۰ دقیقه بهم بگو …» is a RECURRING SCHEDULE.

The sweep caught it SPEAKING ONCE immediately (routed to speech) and
storing nothing — the repeating interval with a «بگو» verb never
entered the scheduler. The gate now takes every repeating-interval
sentence; the stored action is the operator's words with the interval
clause and the «یکبار» filler stripped; the registration names BOTH
the interval and the action.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%آب بخورم-r65%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%آب بخورم-r65%'")


class TestTheRecurringSpeech:
    def test_it_registers_a_schedule_not_a_one_shot_speech(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        p = route_and_run("هر ۳۰ دقیقه یکبار بهم بگو آب بخورم-r65")
        assert p["ok"] is True
        assert p["route"] == ["scheduler"]  # never an immediate speech run
        rep = p["agent_report"]
        assert "تکراری ثبت شد" in rep and "هر ۳۰ دقیقه" in rep
        assert "آب بخورم-r65" in rep  # the action is named
        rows = DatabaseSuite.shared_persistent().query(
            "SELECT command, every_minutes FROM schedules "
            "WHERE command LIKE '%آب بخورم-r65%'").get("rows", [])
        assert rows and int(rows[0]["every_minutes"]) == 30
        assert rows[0]["command"] == "بهم بگو آب بخورم-r65"  # no «یکبار» filler

    def test_the_plain_recurring_reminder_still_works(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("هر روز ساعت ۸ صبح بهم یادآوری کن دارو بخورم-r65")
        assert p["ok"] is True
        assert p["route"] == ["scheduler"]
