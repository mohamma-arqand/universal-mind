"""R76 P1-P5 — the REMINDER-QUESTION class.

A live 14-command sweep found 8 wrong answers: «چند تا یادآور برای فردا
داری؟» REGISTERED a new reminder (!), «بزرگترین یادآور» answered with
chain statistics, «آخرین یادآورم» showed system vitals, sorting fell to
a data mean of nothing, and searching inside reminders was unknown. The
class: every question about the reminders answers from the REAL
schedules table — and question words close the registration gate.
"""

from __future__ import annotations

import pytest


def _cleanup(probe_rows: tuple[str, ...] = ("گواه-r76t",)) -> None:
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite(persistent=True)
    for tag in probe_rows:
        db.execute(f"DELETE FROM schedules WHERE command LIKE '%{tag}%'")


class TestQuestionGate:
    def test_a_count_ask_never_registers(self) -> None:
        from universal_mind.scheduler import list_schedules

        from universal_mind.persian_router import route_and_run

        _cleanup()
        before = len(list_schedules())
        p = route_and_run("چند تا یادآور برای فردا داری؟")
        assert p["ok"] is True
        assert p["route"] == ["reflexive"], p["route"]
        after = len(list_schedules())
        assert after == before, f"a question registered {after - before} rows!"

    def test_a_registration_still_registers(self) -> None:
        from universal_mind.scheduler import list_schedules

        from universal_mind.persian_router import route_and_run

        _cleanup()
        before = len(list_schedules())
        p = route_and_run("یادم بنداز که پس‌فردا ساعت ۷ گواه-r76t کنفرانس")
        assert p["ok"] is True and "scheduler" in p["route"]
        assert len(list_schedules()) == before + 1
        _cleanup()

    def test_the_plain_list_survives(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("یادآورهای من")
        assert p["ok"] is True and "scheduler" in p["route"]


class TestAnswers:
    def test_the_count_answers_from_the_real_table(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("چند تا یادآور داری؟")
        rep = str(p.get("agent_report", ""))
        assert "یادآور داری" in rep

    def test_the_longest_reminder_is_named(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("بزرگترین یادآور من کدام است؟")
        rep = str(p.get("agent_report", ""))
        assert "موفقترین" not in rep, "chain statistics leaked in"
        assert ("بلندترین یادآورت" in rep) or ("هیچ یادآوری" in rep)

    def test_the_oldest_and_newest_come_from_the_table(self) -> None:
        from universal_mind.persian_router import route_and_run

        for cmd, needle in (("قدیمیترین یادآور من کدام است؟", "قدیمیترین یادآورت"),
                            ("آخرین یادآورم چی بود؟", "جدیدترین یادآورت")):
            rep = str(route_and_run(cmd).get("agent_report", ""))
            assert (needle in rep) or ("هیچ یادآوری" in rep), cmd

    def test_search_inside_reminders(self) -> None:
        from universal_mind.persian_router import route_and_run

        p = route_and_run("در یادآورهایم دنبال جلسه بگرد")
        rep = str(p.get("agent_report", ""))
        assert ("یادآور با «جلسه»" in rep) or ("پیدا نکردم" in rep)

    def test_sorting_answers_with_the_rows(self) -> None:
        from universal_mind.persian_router import route_and_run

        for cmd in ("یادآورهایم را بر اساس زمان مرتب کن",
                    "همه یادآورهایم را از قدیم به جدید نشان بده",
                    "یادآورهایم را حرف به حرف مرتب کن"):
            p = route_and_run(cmd)
            rep = str(p.get("agent_report", ""))
            assert p["ok"] is True, cmd
            assert ("به ترتیب" in rep) or ("هیچ یادآوری" in rep), cmd
            assert "مرتب شد (صعودی): ۲" not in rep, "the data mean leaked in"


@pytest.fixture(autouse=True)
def _around() -> None:
    _cleanup()
    yield
    _cleanup()
