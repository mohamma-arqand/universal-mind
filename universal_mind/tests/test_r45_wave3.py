"""Tests: R45 wave-3 — the self-aware mind: purge, status, advice, harvest.

Live laws:
1. The unknown-noise purge is a REPORTED one-time migration: dry-run
   counts without writing, --apply marks exactly the route-less rows,
   and the run_history WRITER now stamps 'unknown_noise' itself so the
   poison can never silently return.
2. «وضعیت خودت چطور است؟» answers with five real signals (pulse, drift,
   backup, verdicts, red-team) — a dead gauge says «—», never hides.
3. «پیشنهاد بده» derives hot routes, the best route, and never-used
   capabilities from the REAL store; an empty store says so.
4. An honest refusal HARVESTS its unknown words; the tick's top-5 list
   and «چه واژههایی را نمیشناسی؟» read the same table back.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite


def _db(tmp_path: Path) -> DatabaseSuite:
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(str(tmp_path / "w3.db"))
    RunHistory(db)
    now = dt.datetime.now()
    for back, route, ok, exc in (
        (0, "data", 1, 0.95), (1, "data", 1, 0.9),
        (2, "pdf", 1, 0.8), (3, "chart", 1, 0.7),
    ):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('کار','{route}',{ok},{exc},'', '{ts}')"
        )
    return db


def _router(db: DatabaseSuite) -> Any:
    from universal_mind.persian_router import route_and_run

    def _run(cmd: str) -> dict[str, Any]:
        with patch.object(
            DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)
        ):
            return route_and_run(cmd)

    return _run


class TestNoisePurge:
    def test_dry_run_counts_only(self, tmp_path: Path) -> None:
        db = _db(tmp_path)
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            "VALUES ('noise','','0','', '', '2026-01-01 00:00:00')"
        )
        from universal_mind.noise_purge import purge_unknown_noise

        info = purge_unknown_noise(db=db, apply=False)
        assert info["rows_found"] == 1 and info["rows_updated"] == 0
        left = db.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE route='' AND (outcome_class IS NULL OR outcome_class='')"
        )["rows"][0]["n"]
        assert left == 1  # dry run wrote nothing

    def test_apply_marks_and_reports(self, tmp_path: Path) -> None:
        db = _db(tmp_path)
        for _ in range(3):
            db.execute(
                "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
                "VALUES ('noise','','0','', '', '2026-01-01 00:00:00')"
            )
        from universal_mind.noise_purge import purge_unknown_noise

        info = purge_unknown_noise(db=db, apply=True)
        assert info["rows_updated"] == 3
        left = db.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE route='' AND (outcome_class IS NULL OR outcome_class='')"
        )["rows"][0]["n"]
        assert left == 0

    def test_writer_stamps_noise_law(self, tmp_path: Path) -> None:
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(str(tmp_path / "law.db"))
        hist = RunHistory(db)
        hist.record("بیثبات", [], False)  # no route, no class
        row = db.query(
            "SELECT outcome_class FROM run_history WHERE command='بیثبات'"
        )["rows"][0]
        assert row["outcome_class"] == "unknown_noise"


class TestSelfStatus:
    def test_five_signals_answer(self, tmp_path: Path) -> None:
        db = _db(tmp_path)
        run = _router(db)
        p = run("وضعیت خودت چطور است؟")
        rep = p["agent_report"]
        for name in ("تپش", "رانش کارایی", "بکاپ", "رأیهای تو", "تیم سرخ"):
            assert name in rep


class TestSuggest:
    def test_advice_from_real_runs(self, tmp_path: Path) -> None:
        db = _db(tmp_path)
        run = _router(db)
        p = run("پیشنهاد بده")
        rep = p["agent_report"]
        assert "«data» (۲ بار)" in rep          # hot route from the real week
        assert "داوری ۹۲٪" in rep               # best route: avg(0.95, 0.90)
        assert "امتحان کن" in rep               # never-used capabilities named

    def test_empty_store_is_honest(self, tmp_path: Path) -> None:
        from universal_mind.run_history import RunHistory

        db = DatabaseSuite(str(tmp_path / "empty.db"))
        RunHistory(db)
        run = _router(db)
        p = run("پیشنهاد بده")
        assert "هنوز چیزی برای پیشنهاد ندارم" in p["agent_report"]


class TestUnknownHarvest:
    def test_refusal_harvests_and_answers(self, tmp_path: Path) -> None:
        db = DatabaseSuite(str(tmp_path / "uh.db"))
        run = _router(db)
        r1 = run("فلانbabایی را باطلا کن")   # unknown → honest refusal
        assert r1["ok"] is False
        r1b = run("فلانbabایی را باطلا کن")  # said twice — the habit counts
        assert r1b["ok"] is False
        r2 = run("چه واژههایی را نمیشناسی؟")
        assert "«فلانbabایی»" in r2["agent_report"]
        assert "(۲ بار)" in r2["agent_report"]  # both refusals harvested

    def test_top_unknowns_ranked(self, tmp_path: Path) -> None:
        from universal_mind.unknown_harvest import harvest_unknown, top_unknowns

        db = DatabaseSuite(str(tmp_path / "rank.db"))
        harvest_unknown(["کیوی", "موز"], db=db)
        harvest_unknown(["کیوی"], db=db)
        terms = top_unknowns(5, db=db)
        assert terms[0]["term"] == "کیوی" and terms[0]["hits"] == 2
        assert terms[1]["term"] == "موز" and terms[1]["hits"] == 1
