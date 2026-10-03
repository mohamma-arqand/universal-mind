"""R67 P1 — «یادآوری N را غیرفعال/فعال کن»: the TOGGLE.

Pausing a reminder is NOT deleting it — the row survives, active
flips. Both shapes answer with the row named (id + text); an unknown
id is the same honest refusal as the delete.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def probe_row() -> dict[str, object]:
    from universal_mind.scheduler import delete_schedule, list_schedules, register

    register("هر روز ساعت ۷ گواه-r67-p1 را بگو")
    sid = next(
        s.schedule_id for s in list_schedules()
        if "گواه-r67-p1" in s.command
    )
    yield {"id": sid}
    try:
        delete_schedule(sid)
    except Exception:  # noqa: BLE001 — cleanup only
        pass


def _fa(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _active(sid: int) -> bool:
    from universal_mind.scheduler import list_schedules

    return next(s.active for s in list_schedules() if s.schedule_id == sid)


class TestTheToggle:
    def test_off_flips_active_and_the_row_survives(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری {_fa(sid)} را غیرفعال کن")
        assert p["ok"] is True
        assert _active(sid) is False            # really disarmed
        # the row is NOT deleted
        from universal_mind.scheduler import list_schedules

        assert any(s.schedule_id == sid for s in list_schedules())
        assert "غیرفعال" in p["agent_report"]
        assert "گواه-r67-p1" in p["agent_report"]  # the row is named

    def test_on_rearms(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        route_and_run(f"یادآوری {_fa(sid)} را غیرفعال کن")
        p = route_and_run(f"یادآوری {_fa(sid)} را فعال کن")
        assert p["ok"] is True
        assert _active(sid) is True
        assert "فعال" in p["agent_report"]

    def test_the_pause_names_the_delete_recipe(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run

        sid = int(probe_row["id"])
        p = route_and_run(f"یادآوری {_fa(sid)} را غیرفعال کن")
        # a paused row is not lost — the honest path to removal is named
        assert "حذف کن" in p["agent_report"]

    def test_an_unknown_id_is_an_honest_refusal(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآوری ۹۹۹۹۹ را غیرفعال کن")
        assert p["ok"] is False
        assert "پیدا نکردم" in p["agent_report"]

    def test_a_toggle_never_deletes(self, probe_row) -> None:
        from universal_mind.persian_router import route_and_run
        from universal_mind.scheduler import list_schedules

        sid = int(probe_row["id"])
        route_and_run(f"یادآوری {_fa(sid)} را غیرفعال کن")
        route_and_run(f"یادآوری {_fa(sid)} را فعال کن")
        route_and_run(f"یادآوری {_fa(sid)} را غیرفعال کن")
        assert any(s.schedule_id == sid for s in list_schedules())
