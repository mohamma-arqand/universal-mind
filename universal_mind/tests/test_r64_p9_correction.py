"""R64 P9 — «نه منظورم فردا ساعت ۹ بود»: re-time the LAST reminder.

The correction sentence speaks of the reminder by POSITION, not by
name. Three honest outcomes (all live-proved):
- a real re-time: the run_at is UPDATED and both sides are named
  («۲۰۲۶-۱۰-۰۴T۰۷:۰۰» → «T۰۸:۰۰»);
- a correction that changes nothing says so («همین‌طور … است»);
- a PAST correction («دیشب بود») is refused by name — a reminder
  cannot fire in the past.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64-corr%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r64-corr%'")


class TestTheCorrection:
    def test_a_real_retime_updates_and_names_both_sides(self) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۷ گواه-r64-corr را بدهکار کن")
        p = route_and_run("منظورم فردا ساعت ۸ بود")
        assert p["ok"] is True
        assert "عوض کردم" in p["agent_report"]
        assert "۰۸:۰۰" in p["agent_report"] and "۰۷:۰۰" in p["agent_report"]
        rows = DatabaseSuite.shared_persistent().query(
            "SELECT run_at FROM schedules WHERE command LIKE '%گواه-r64-corr%'"
        ).get("rows", [])
        assert rows and "08:00" in str(rows[0]["run_at"])  # really updated

    def test_a_no_change_correction_says_so(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۷ گواه-r64-corr را بدهکار کن")
        p = route_and_run("منظورم فردا ساعت ۷ بود")
        assert p["ok"] is True
        assert "چیزی عوض نشد" in p["agent_report"]

    def test_a_past_correction_is_refused_by_name(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۷ گواه-r64-corr را بدهکار کن")
        p = route_and_run("نه منظورم دیشب بود")
        assert p["ok"] is False
        rep = p["agent_report"]
        assert "گذشته" in rep and "دیشب" in rep
        assert "نمی‌توان" in rep
