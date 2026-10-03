"""R66 P4 — «یادآوری شماره N را نشان بده»: the SINGLE-REMINDER VIEW.

The sweep caught the sentence unrecognized while the operator's most
literal ask — «I named the number, show me THAT one» — fell to a
generic shrug. One number → one row (id, text, fire time, active);
an unknown id is an honest refusal, never a wrong row.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def probe_row() -> dict[str, object]:
    from universal_mind.scheduler import delete_schedule, list_schedules, register

    register("هر روز ساعت ۷ گواه-r66-p4 را بگو")
    sid = next(
        s.schedule_id for s in list_schedules()
        if "گواه-r66-p4" in s.command
    )
    yield {"id": sid}
    try:
        delete_schedule(sid)
    except Exception:  # noqa: BLE001 — cleanup only
        pass


def _fa(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


class TestTheSingleReminderView:
    def test_one_number_returns_one_row(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری شماره {_fa(sid)} را نشان بده")
        assert p["ok"] is True
        assert p["route"] == ["scheduler"]
        assert p["result"]["id"] == sid
        assert "گواه-r66-p4" in p["agent_report"]
        assert "فعال" in p["agent_report"]

    def test_the_fire_time_is_in_the_report_persian(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری شماره {_fa(sid)} را نشان بده")
        assert "ساعت ۷:۰۰" in p["agent_report"]  # Persian digits, no latin 7

    def test_an_unknown_id_is_an_honest_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآوری شماره ۹۹۹۹۹ را نشان بده")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]

    def test_the_word_یادآور_shape_works_too(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآور شماره {_fa(sid)} را نشان بده")
        assert p["ok"] is True
        assert "گواه-r66-p4" in p["agent_report"]
