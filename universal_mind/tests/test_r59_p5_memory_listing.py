"""R59 P5 — memory listings: what do you remember, and what was the latest.

The sweep measured both questions dying in «نشناختم» while named_memory
already had recall_facts(). A listing is not a recall-by-question (M3): it
needs no question marks — just the real rows, numbered, newest first.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.reflexive import answer_reflexive


def _db_with_facts(*facts: str) -> DatabaseSuite:
    db = DatabaseSuite(str(Path(mkdtemp(prefix="um-p5-")) / "mem.db"))
    from universal_mind.named_memory import ensure_table, save_fact

    ensure_table(db)
    for f in facts:
        save_fact(f, db=db)
    return db


def _with(db: DatabaseSuite) -> object:
    return patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db))


class TestListMemory:
    def test_the_sweep_question_lists_the_real_rows(self) -> None:
        db = _db_with_facts("جلسه شنبه ساعت ۱۰ است", "قبض برق را پرداخت کن")
        with _with(db):
            out = answer_reflexive("چه چیزهایی یادت هست؟")
        assert out is not None
        rep = out["agent_report"]
        assert "۲ چیز یادم است" in rep
        assert "جلسه شنبه" in rep and "قبض برق" in rep

    def test_numbered_in_persian(self) -> None:
        import re

        db = _db_with_facts("یک", "دو")
        with _with(db):
            rep = answer_reflexive("چه چیزهایی یادت هست؟")["agent_report"]
        assert "۱." in rep and "۲." in rep
        assert not re.search(r"[0-9]\.", rep)

    def test_empty_is_honest_with_the_remedy(self) -> None:
        db = _db_with_facts()
        with _with(db):
            rep = answer_reflexive("چه چیزهایی یادت هست؟")["agent_report"]
        assert "هیچ چیزی یادم نیست" in rep
        assert "یادت باشد" in rep

    def test_the_latest_question_answers_the_newest_row(self) -> None:
        db = _db_with_facts("قدیمی‌ترین", "تازه‌ترین یادداشت")
        with _with(db):
            out = answer_reflexive("آخرین چیزی که یادت داشت چی بود؟")
        assert out is not None
        assert "تازه‌ترین یادداشت" in out["agent_report"]

    def test_the_save_verb_is_never_mistaken_for_a_listing(self) -> None:
        db = _db_with_facts("یک")
        with _with(db):
            out = answer_reflexive("یادت باشد راز تازه است")
        assert out is None or "چیز یادم است" not in out["agent_report"]

    def test_a_dead_store_says_the_honest_empty(self) -> None:
        class _Boom:
            def query(self, *a: object, **k: object) -> object:
                raise RuntimeError("gone")

        with patch.object(DatabaseSuite, "shared_persistent",
                          classmethod(lambda cls: _Boom())):  # type: ignore[arg-type]
            out = answer_reflexive("چه چیزهایی یادت هست؟")
        assert out is None or "یادم نیست" in out["agent_report"]
