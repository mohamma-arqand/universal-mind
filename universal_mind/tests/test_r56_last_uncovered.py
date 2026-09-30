"""R56 — the last two uncovered modules, tested against their REAL stores.

named_memory: the operator's natural way of making a memory
(«یادت باشد ...») — parse the request, save the fact, recall it, forget it
by match, surface it for a later command.

self_status: «وضعیت خودت چطور است؟» — the five-signal health answer, each
signal read live, every missing signal NAMED (the platform's honesty law).
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestNamedMemory:
    def test_parse_remember_request_extracts_the_fact(self) -> None:
        from universal_mind.named_memory import parse_remember_request

        got = parse_remember_request("یادت باشد که مدیر پروژه آقای رضایی است")
        assert got is not None
        fact = got.get("fact") if isinstance(got, dict) else got
        assert "رضایی" in str(fact)

    def test_parse_returns_none_for_an_ordinary_command(self) -> None:
        from universal_mind.named_memory import parse_remember_request

        # an ordinary work command is NOT a memory request
        assert parse_remember_request("نمودار بکش") is None

    def test_save_and_recall_roundtrip(self, tmp_path: Path) -> None:
        """A saved fact comes back with its REAL text (persistent store)."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.named_memory import recall_facts, save_fact

        db = DatabaseSuite(str(tmp_path / "nm.db"))
        res = save_fact("پروژه من «ذهن جهانی» است", db=db)
        assert res.get("ok") is True
        facts = recall_facts(limit=5, db=db)
        text = " ".join(str(f.get("fact", f)) for f in facts)
        assert "ذهن جهانی" in text

    def test_recall_respects_the_limit(self, tmp_path: Path) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.named_memory import recall_facts, save_fact

        db = DatabaseSuite(str(tmp_path / "nm2.db"))
        for i in range(5):
            save_fact(f"واقعیت شماره {i}", db=db)
        facts = recall_facts(limit=2, db=db)
        assert len(facts) <= 2

    def test_forget_matching_removes_the_fact(self, tmp_path: Path) -> None:
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.named_memory import forget_matching, recall_facts, save_fact

        db = DatabaseSuite(str(tmp_path / "nm3.db"))
        save_fact("رنگ مورد علاقه من آبی است", db=db)
        before = recall_facts(limit=5, db=db)
        assert any("آبی" in str(f) for f in before)
        forget_matching("آبی", db=db)
        after = recall_facts(limit=5, db=db)
        assert not any("آبی" in str(f) for f in after)

    def test_surface_for_command_is_read_only(self, tmp_path: Path) -> None:
        """Surfacing a memory never mutates the store (a lens, not a writer)."""
        from universal_mind.database_suite import DatabaseSuite
        from universal_mind.named_memory import recall_facts, save_fact, surface_for_command

        db = DatabaseSuite(str(tmp_path / "nm4.db"))
        save_fact("مدیر پروژه آقای رضایی است", db=db)
        before = len(recall_facts(limit=50, db=db))
        surface_for_command("گزارش مدیر پروژه را بساز", db=db)
        after = len(recall_facts(limit=50, db=db))
        assert after == before


class TestSelfStatus:
    def test_five_signals_report_is_persian_and_complete(self) -> None:
        """The live answer carries the five real signals, all named."""
        from universal_mind.self_status import self_status

        res = self_status()
        assert res["ok"] is True
        report = str(res.get("report", ""))
        assert "وضعیت خودم" in report
        # the five signal names in the report
        for label in ("تپش", "رانش", "بکاپ", "رأی", "تیم سرخ"):
            assert label in report, f"missing signal: {label}"

    def test_signals_dict_is_structured(self) -> None:
        from universal_mind.self_status import self_status

        res = self_status()
        signals = res.get("signals") or {}
        assert set(signals) >= {"pulse", "drift", "backup", "verdicts", "red_team"}
        # every signal line is non-empty Persian text
        for key, line in signals.items():
            assert str(line).strip(), f"empty signal: {key}"

    def test_a_broken_store_never_crashes_the_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """THE HONESTY LAW: a dead store yields a NAMED line, never an exception."""
        from universal_mind import self_status as ss

        class _Boom:
            def query(self, *a, **k):  # type: ignore[no-untyped-def]
                raise RuntimeError("store is gone")

            def execute(self, *a, **k):  # type: ignore[no-untyped-def]
                raise RuntimeError("store is gone")

        res = ss.self_status(db=_Boom())  # type: ignore[arg-type]
        assert res["ok"] is True  # the answer still arrives
        assert str(res.get("report", "")).strip()

    def test_fa_formats_numbers_in_persian(self) -> None:
        from universal_mind.self_status import _fa

        assert _fa(7) == "۷"
        assert _fa("12") == "۱۲"
