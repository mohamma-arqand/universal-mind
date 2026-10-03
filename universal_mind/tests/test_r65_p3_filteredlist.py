"""R65 P3 — «یادآورهای فردا را نشان بده» is a FILTERED LIST, not a registration.

The sweep caught it REGISTERING a fresh reminder (defaulted hour 8)
instead of listing. The listing gate takes the time-filter shapes;
rows are filtered to the named day (one-shots by date, recurring always
shown); «پس‌فردا» is matched LONGEST-FIRST («فردا» is its substring).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clean():
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r65%'")
    yield
    DatabaseSuite.shared_persistent().execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r65%'")


class TestTheFilteredListing:
    def test_tomorrow_lists_only_tomorrow(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه فردا ساعت ۷ گواه-r65 را بدهکار کن")
        route_and_run("یادم باشه پس‌فردا ساعت ۵ گواه-r65 بعدی")
        p = route_and_run("یادآورهای فردا را نشان بده")
        rep = p["agent_report"]
        assert p["route"] == ["scheduler"]
        assert "(فردا)" in rep
        assert "گواه-r65 را بدهکار" in rep  # tomorrow's row shows
        assert "گواه-r65 بعدی" not in rep   # day-after's row does not
        # and NOTHING new was registered by the listing itself
        rows_after = DatabaseSuite_count("گواه-r65")
        assert rows_after == 2  # the two we made — no third from the list ask

    def test_day_after_is_not_caught_by_tomorrow_substring(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه پس‌فردا ساعت ۵ گواه-r65 بعدی")
        p = route_and_run("یادآورهای پس‌فردا را نشان بده")
        rep = p["agent_report"]
        assert "(پس‌فردا)" in rep
        assert "گواه-r65 بعدی" in rep

    def test_today_with_nothing_is_honest(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآورهای امروز را نشان بده")
        rep = p["agent_report"]
        assert ("هیچ یادآوریِ امروز" in rep) or ("(امروز)" in rep)


def DatabaseSuite_count(needle: str) -> int:
    from universal_mind.database_suite import DatabaseSuite

    q = DatabaseSuite.shared_persistent().query(
        f"SELECT COUNT(*) n FROM schedules WHERE command LIKE '%{needle}%'")
    return int(q["rows"][0]["n"]) if q.get("ok") else 0
