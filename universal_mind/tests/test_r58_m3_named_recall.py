"""R58 M3 — recall the named memory by ASKING.

Measured gap (the 18-command sweep): «یادت باشد جلسه شنبه ساعت ۱۰ است» saves a
named_memory row, but «جلسه شنبه چه ساعتی است؟» returned «نشناختم». A question
whose words overlap a stored fact is now answered FROM that fact — and a
question about something never stored is never invented.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.reflexive import answer_reflexive


def _db_with_fact(fact: str) -> DatabaseSuite:
    db = DatabaseSuite(str(Path(mkdtemp(prefix="um-m3-")) / "mem.db"))
    from universal_mind.named_memory import ensure_table, save_fact

    ensure_table(db)
    save_fact(fact, db=db)
    return db


class TestRecallByName:
    def test_the_sweep_question_is_answered_from_memory(self) -> None:
        db = _db_with_fact("جلسه شنبه ساعت ۱۰ است")
        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
            out = answer_reflexive("جلسه شنبه چه ساعتی است؟")
        assert out is not None
        assert "جلسه شنبه ساعت ۱۰ است" in out["agent_report"]
        assert "یادم است" in out["agent_report"]

    def test_a_question_about_something_never_stored_is_not_invented(self) -> None:
        db = _db_with_fact("جلسه شنبه ساعت ۱۰ است")
        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
            out = answer_reflexive("شماره تلفن علی چیه؟")
        # no overlapping fact → the reflex stays quiet (None) or answers from
        # ANOTHER honest class — never fabricates a phone number
        if out is not None:
            assert "شماره" not in out["agent_report"] or "نمی" in out["agent_report"]

    def test_a_save_command_is_not_mistaken_for_a_question(self) -> None:
        # «یادت باشد …» must keep its own path and never be answered as a recall
        db = _db_with_fact("جلسه شنبه ساعت ۱۰ است")
        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
            out = answer_reflexive("یادت باشد رنگ ماشین آبی است")
        assert out is None or "یادم است" not in out["agent_report"]

    def test_multiple_hits_are_named_not_guessed(self) -> None:
        db = _db_with_fact("قرار اداری شنبه ساعت ۸ است")
        from universal_mind.named_memory import save_fact

        save_fact("قرار ورزشی شنبه ساعت ۶ است", db=db)
        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
            out = answer_reflexive("قرار شنبه چه ساعتی است؟")
        assert out is not None
        # both facts share قرار+شنبه with the question → both are named,
        # neither is silently picked
        assert "چند مورد" in out["agent_report"]
        assert "قرار اداری" in out["agent_report"] and "قرار ورزشی" in out["agent_report"]

    def test_a_dead_store_never_breaks_the_reflex(self) -> None:
        class _Boom:
            def query(self, *a: object, **k: object) -> object:
                raise RuntimeError("gone")

        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: _Boom())):  # type: ignore[arg-type]
            out = answer_reflexive("جلسه شنبه چه ساعتی است؟")
        # the lens failed → fall through honestly (None or another class),
        # never an exception, never a fabricated memory
        assert out is None or "یادم است" not in out["agent_report"]

    def test_the_answer_cites_where_it_came_from(self) -> None:
        db = _db_with_fact("جلسه شنبه ساعت ۱۰ است")
        with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
            out = answer_reflexive("جلسه شنبه چه ساعتی است؟")
        assert out is not None
        assert "حافظهٔ نامدار" in out["agent_report"]
