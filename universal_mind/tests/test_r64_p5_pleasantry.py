"""R64 P5 — the pleasantry is not the reminder.

«خسته نباشی، یادم باشه فردا ساعت ۱۰ دارو بخورم» stored the WHOLE
sentence as the reminder text — the greeting rode in. The pleasantries
(سلام/خسته نباشی/مرسی/…) are now stripped from the body and
ACKNOWLEDGED by name in the answer; the stored reminder carries only
the operator's actual words.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")


class TestThePleasantReminder:
    def test_the_greeting_is_acknowledged_and_stripped(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        p = route_and_run("خسته نباشی، یادم باشه فردا ساعت ۷ گواه-r64 را بدهکار کن")
        assert p["ok"] is True
        rep = p["agent_report"]
        assert "خسته نباشی" in rep  # acknowledged by name
        rows = DatabaseSuite.shared_persistent().query(
            "SELECT command FROM schedules WHERE command LIKE '%گواه-r64%'"
        ).get("rows", [])
        assert rows, "the reminder must be stored"
        stored = rows[0]["command"]
        assert "خسته نباشی" not in stored  # the pleasantry never rides in
        assert "گواه-r64" in stored

    def test_a_plain_reminder_unchanged(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادم باشه فردا ساعت ۷ گواه-r64 را بدهکار کن")
        assert p["ok"] is True
        assert "همبستی" not in p["agent_report"]  # no greeting, no ack
