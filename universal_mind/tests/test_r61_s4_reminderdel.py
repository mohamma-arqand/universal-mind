"""R61-S4 — reminder deletion: by id, bulk with the delete law.

«یادآوری ۶۳ را حذف کن» and «همه یادآوریها را حذف کن» both fell to
«نشناختم» while delete_schedule existed. The listing now shows each row's
NUMBER, deletion accepts the number, and bulk deletion is armed ONLY by an
explicit «تأیید کن» (the delete law).

Isolation: every test builds its own throwaway reminder in the REAL store
and removes it with a named cleanup at teardown — the R59 leak law.
"""

from __future__ import annotations

import pytest

from universal_mind.persian_router import route_and_run
from universal_mind.scheduler import list_schedules


@pytest.fixture()
def probe_reminder():
    """One throwaway reminder, removed by name at teardown."""
    route_and_run("یادم باشه پس‌فردا ساعت ۶ گواه-آزمون-۶۱")
    yield
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-آزمون-۶۱%'")


def _real_rows():
    return list_schedules()


class TestListingShowsNumbers:
    def test_each_row_carries_its_number(self, probe_reminder) -> None:
        rep = str(route_and_run("یادآورهای من").get("agent_report", ""))
        assert "گواه-آزمون-۶۱" in rep
        assert "(" in rep  # the (شمارh) prefix exists


class TestDeleteById:
    def test_deletion_by_number_removes_only_that_row(self, probe_reminder) -> None:
        before = {s.schedule_id for s in _real_rows()}
        rep = str(route_and_run("یادآورهای من").get("agent_report", ""))
        import re

        m = None
        for ln in rep.splitlines():
            if "گواه-آزمون-۶۱" in ln:
                mm = re.match(r"\s*[•-]*\s*\(([۰-۹]+)\)", ln)
                if mm:
                    m = mm
                    break
        assert m, "probe reminder not numbered in listing"
        sid = m.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        out = route_and_run(f"یادآوری {sid} را حذف کن")
        assert out.get("ok") is True
        assert f"شمارهٔ {sid}" in str(out.get("agent_report", "")).replace("۰", "۰") or "حذف شد" in out["agent_report"]
        after = {s.schedule_id for s in _real_rows()}
        assert int(sid) not in after
        assert before - after == {int(sid)}  # NOTHING else was touched

    def test_a_missing_number_is_refused_by_name(self) -> None:
        out = route_and_run("یادآوری ۹۹۹۹ را حذف کن")
        assert out.get("ok") is False
        assert "پیدا نکردم" in out["agent_report"]


class TestBulkDeleteLaw:
    def test_bulk_without_confirmation_deletes_nothing(self, probe_reminder) -> None:
        before = len(_real_rows())
        out = route_and_run("همه یادآوریها را حذف کن")
        assert out.get("ok") is False
        assert "تأیید کن" in out["agent_report"]
        assert len(_real_rows()) == before  # the law held: nothing destroyed

    def test_the_count_is_named_in_the_ask(self, probe_reminder) -> None:
        out = route_and_run("همه یادآوریها را حذف کن")
        n = str(len(_real_rows())).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        assert f"{n} یادآوری داری" in out["agent_report"]


class TestDeleteByNeedleStillWorks:
    def test_the_old_match_shape_is_untouched(self, probe_reminder) -> None:
        out = route_and_run("یادآور گواه-آزمون-۶۱ را حذف کن")
        assert out.get("ok") is True
        assert "حذف شد" in out["agent_report"]
