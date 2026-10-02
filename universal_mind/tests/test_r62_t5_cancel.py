"""R62 T5 — cancel/undo: the honest refusal that names the last run.

«لغو کن» / «برگرد عقب» demanded a universal undo — a lie this platform
refuses to tell (a fired reminder, a written file, a spoken word each
unwind differently). The answer names WHAT the last run did (from the
real history) and teaches the exact per-effect remedy.
"""

from __future__ import annotations

import pytest

from universal_mind.reflexive import answer_reflexive


@pytest.fixture(autouse=True)
def _probe_last_run():
    # a REAL run through the router writes history in whatever store the
    # test's isolate gives it — the cancel answer must read THAT store.
    from universal_mind.persian_router import route_and_run

    route_and_run("محتوای فایل D:/گواه-آزمون-لغو-نشان-نده.txt را نشان بده")
    yield


def _ans(cmd: str) -> str:
    a = answer_reflexive(cmd)
    assert a is not None, cmd
    return a["agent_report"]


class TestTheHonestRefusal:
    def test_cancel_answers_never_dead(self) -> None:
        rep = _ans("لغو کن")
        assert "لغوِ خودکار نمی‌کنم" in rep

    def test_the_last_run_is_named(self) -> None:
        rep = _ans("برگرد عقب")
        assert "گواه-آزمون-لغو" in rep  # the probe run itself is the last run

    def test_a_reminder_run_gets_the_reminder_remedy(self) -> None:
        from universal_mind.persian_router import route_and_run

        route_and_run("یادم باشه پس‌فردا ساعت ۶ گواه-یادآور-لغو")
        try:
            rep = _ans("لغو کن")
            assert "یادآوری N را حذف کن" in rep
        finally:
            from universal_mind.database_suite import DatabaseSuite

            DatabaseSuite.shared_persistent().execute(
                "DELETE FROM schedules WHERE command LIKE '%گواه-یادآور-لغو%'")

    def test_a_file_run_gets_the_file_remedy(self) -> None:
        # the fixture's probe run IS a textfile run — its remedy names the law
        rep = _ans("لغو کن")
        assert "تأیید کن" in rep  # the delete law is named


class TestTheGateIsNarrow:
    def test_a_sentence_about_cancelling_is_not_a_cancel(self) -> None:
        # a QUESTION about the mechanism is not a bare command
        assert answer_reflexive("حذف فایلها چطور کار می‌کند؟") is None
