"""R58 M4 — the upcoming agenda, read from the real store.

Measured gap (the 18-command sweep): «هفته بعد چی کار دارم؟» returned
«نشناختم» while the truth already lived in two tables. The agenda view reads
schedules (one-shot soonest-first + repeating) and time-bearing named notes;
empty is said honestly.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.reflexive import answer_reflexive


def _fresh_db() -> DatabaseSuite:
    return DatabaseSuite(str(Path(mkdtemp(prefix="um-m4-")) / "agenda.db"))


def _with_db(db: DatabaseSuite) -> object:
    return patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db))


class TestAgenda:
    def test_the_exact_sweep_question_answers_from_the_store(self) -> None:
        db = _fresh_db()
        from universal_mind.named_memory import ensure_table, save_fact
        from universal_mind.scheduler import register, register_one_shot

        ensure_table(db)
        with _with_db(db):
            # the REAL registration paths: register() takes the Persian
            # sentence; a ONE-SHOT needs a parseable time in it (the platform
            # honestly refuses a reminder with no when — that is its law, and
            # the test respects it instead of bypassing it)
            register("هر روز ساعت ۸ گزارش صبح را بده")
            reg = register_one_shot("یادم بنداز که فردا جلسه با مدیر را یادآوری کن")
            assert reg.get("ok") is True, f"one-shot refused: {reg}"
            save_fact("جلسه شنبه ساعت ۱۰ است", db=db)
            out = answer_reflexive("برنامه‌ام را نشان بده")
        assert out is not None
        rep = out["agent_report"]
        assert "گزارش صبح" in rep and "جلسه با مدیر" in rep

    def test_a_one_shot_comes_before_the_daily(self) -> None:
        db = _fresh_db()
        from universal_mind.scheduler import register, register_one_shot

        with _with_db(db):
            register("هر روز ساعت ۸ گزارش صبح را بده")
            reg = register_one_shot("یادم بنداز که فردا قرار فوری را یادآوری کن")
            assert reg.get("ok") is True
            rep = answer_reflexive("برنامه‌ام را نشان بده")["agent_report"]
        # the one-shot (a dated reminder) is listed with its own bullet and
        # precedes the repeating backbone; assert both are present in order
        assert rep.index("قرار فوری") < rep.index("گزارش صبح")

    def test_a_time_bearing_note_is_listed(self) -> None:
        db = _fresh_db()
        from universal_mind.named_memory import ensure_table, save_fact

        ensure_table(db)
        with _with_db(db):
            save_fact("جلسه شنبه ساعت ۱۰ است", db=db)
            rep = answer_reflexive("هفته بعد چی کار دارم؟")["agent_report"]
        assert "جلسه شنبه" in rep and "یادداشت" in rep

    def test_empty_is_said_honestly_with_the_remedy(self) -> None:
        db = _fresh_db()
        with _with_db(db):
            rep = answer_reflexive("برنامه‌ام را نشان بده")["agent_report"]
        assert "ثبت نشده" in rep
        assert "یادم بنداز" in rep or "یادآور" in rep

    def test_the_other_week_phrase_answers_too(self) -> None:
        db = _fresh_db()
        with _with_db(db):
            out = answer_reflexive("هفته بعد چی کار دارم؟")
        assert out is not None  # honest-empty is still an ANSWER

    def test_a_dead_store_yields_the_honest_empty_not_a_crash(self) -> None:
        class _Boom:
            def query(self, *a: object, **k: object) -> object:
                raise RuntimeError("gone")

        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: _Boom())):  # type: ignore[arg-type]
            out = answer_reflexive("برنامه‌ام را نشان بده")
        assert out is None or "ثبت نشده" in out["agent_report"]
