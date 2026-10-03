"""R66 P1 — THE DELETE LAW COVERS THE SINGLE DELETE TOO.

The live sweep caught «یادآوری ۶۸ را حذف کن» destroying the operator's
REAL reminder with no confirmation — the R61-S4 gate armed only the
bulk shape. A single delete now names WHAT will go (id + text) and
arms only on an explicit «تأیید کن»; the confirmed delete and the
unknown-id refusal are both pinned.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def probe_row() -> dict[str, object]:
    """A REAL schedule row the test owns — never the operator's data."""
    from universal_mind.scheduler import register, list_schedules

    register("هر روز ساعت ۷ گواه-r66-p1 را بگو")
    sid = next(
        s.schedule_id for s in list_schedules()
        if "گواه-r66-p1" in s.command
    )
    yield {"id": sid}
    from universal_mind.scheduler import delete_schedule

    try:
        delete_schedule(sid)
    except Exception:  # noqa: BLE001 — cleanup only
        pass


class TestTheSingleDeleteLaw:
    def test_without_confirmation_nothing_is_deleted(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.scheduler import list_schedules

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری {sid} را حذف کن")
        assert p["ok"] is False
        assert "تأیید" in p["agent_report"]
        assert str(sid) in p["agent_report"] or "شمارهٔ" in p["agent_report"]
        # the row is STILL THERE
        assert any(s.schedule_id == sid for s in list_schedules())

    def test_the_refusal_names_the_row(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری {sid} را حذف کن")
        assert "گواه-r66-p1" in p["agent_report"]  # the text is named

    def test_with_confirmation_it_deletes(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.scheduler import list_schedules

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری {sid} را حذف کن — تأیید کن")
        assert p["ok"] is True
        assert "حذف شد" in p["agent_report"]
        assert not any(s.schedule_id == sid for s in list_schedules())

    def test_an_unknown_id_refuses_honestly(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآوری ۹۹۹۹۹ را حذف کن — تأیید کن")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]
