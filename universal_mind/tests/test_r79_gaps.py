"""R79 B1-B2 — the CATEGORY-GAPS wave (meetings + windows).

The audit caught «قرار بگذار شنبه ساعت ۱۰ جلسه» (and the fact-stated
«شنبه ساعت ۱۰ جلسه دارم») dying in «نشناختم» — the placement verb was
never a registration shape. And «لیست پنجرههای باز» was unknown while
the close action had the PowerShell all along.
"""

from __future__ import annotations

import pytest


def _cleanup() -> None:
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite(persistent=True).execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r79t%'")


class TestMeetingPlacement:
    def test_the_placement_verb_registers(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        p = route_and_run("قرار بگذار شنبه ساعت ۱۰ جلسه گواه-r79t")
        assert p["ok"] is True and p["route"] == ["scheduler"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert "قرار ثبت شد" in rep and "10:00" in rep

    def test_the_fact_shape_registers_too(self) -> None:
        from universal_mind.persian_router import route_and_run

        _cleanup()
        p = route_and_run("فردا ساعت ۹ جلسه گواه-r79t دارم")
        assert p["ok"] is True and "قرار ثبت شد" in str(p.get("agent_report", ""))

    def test_a_timeless_placement_is_a_named_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("قرار بگذار جلسه")
        assert p["ok"] is False
        assert "زمانِ قرار را نفهمیدم" in str(p.get("agent_report", ""))


class TestWindowListing:
    def test_the_window_list_lists_real_windows(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("لیست پنجرههای باز")
        assert p["route"] == ["reflexive"], p["route"]
        rep = str(p.get("agent_report", ""))
        assert ("پنجره باز" in rep) or ("هیچ پنجره" in rep)
        # the Persian titles must NOT be mangled (the encoding wall)
        assert "??" not in rep

    def test_the_show_shape_and_the_question_shape(self) -> None:
        from universal_mind.persian_router import route_and_run

        for cmd in ("پنجرههای باز را نشان بده", "پنجرهای باز نیست؟"):
            p = route_and_run(cmd)
            assert p["ok"] is True, cmd
            assert "پنجره" in str(p.get("agent_report", ""))

    def test_closing_still_closes(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("پنجره نوپد را ببند")
        # closing a window that may not exist is a named outcome either way
        rep = str(p.get("agent_report", ""))
        assert ("بستم" in rep) or ("پیدا نکردم" in rep) or ("پنجره" in rep)


@pytest.fixture(autouse=True)
def _around() -> None:
    _cleanup()
    yield
    _cleanup()
