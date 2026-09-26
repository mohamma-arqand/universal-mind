"""R46 wave 4 — durability of the ordinary day, tested against live runs.

Item 13 — the tick leaves a health row (state/skipped/causes); a FAILED
         tick reaches a toast. A broken store never dies silently.
Item 15 — «بکاپ سالم است؟» answers with proof: fresh+drilled = healthy,
         stale (>7d) = an explicit warning, absent = the path is cut.
"""

from __future__ import annotations

import io
import contextlib
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _fresh_db(monkeypatch: Any, tmp_path: Path) -> DatabaseSuite:
    db = DatabaseSuite(str(tmp_path / "r46w4.db"))
    RunHistory(db)
    monkeypatch.setattr(
        DatabaseSuite, "shared_persistent",
        classmethod(lambda cls: db),
    )
    return db


class TestTickHealth:
    def test_failed_entry_leaves_a_health_row(self, monkeypatch: Any, tmp_path: Path) -> None:
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.scripts.scheduler_tick import tick

        with patch(
            "universal_mind.scheduler.run_due",
            return_value={
                "fired": [{"command": "فرمان آزمون", "ok": False,
                           "error": "دسترس نیست (محیط رد کرد)"}],
                "count": 1,
            },
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                r = tick(notify_summary=False)
        assert r["state"] == "failed"
        assert r["skipped"] == 1
        rows = db.query("SELECT state, skipped, causes FROM tick_health")["rows"]
        assert rows and rows[0]["state"] == "failed"

    def test_healthy_tick_is_ok_and_stamped(self, monkeypatch: Any, tmp_path: Path) -> None:
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.scripts.scheduler_tick import tick

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = tick(notify_summary=False)
        assert r["state"] == "ok"
        rows = db.query("SELECT state FROM tick_health")["rows"]
        assert rows and rows[-1]["state"] == "ok"

    def test_tick_survives_a_broken_store_with_rc0(self, monkeypatch: Any, tmp_path: Path) -> None:
        from universal_mind.scripts.scheduler_tick import tick

        broken = DatabaseSuite(str(tmp_path / "broken.db"))
        # a suite whose every read fails (the corrupted-db shape)
        monkeypatch.setattr(
            DatabaseSuite, "shared_persistent",
            classmethod(lambda cls: broken),
        )
        def _boom(*a: object, **k: object) -> None:
            raise RuntimeError("store locked")
        with patch.object(type(broken), "query", _boom):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                r = tick(notify_summary=False)   # no exception = RC 0
        assert r is not None


class TestBackupHealth:
    def _plant_backup(self, tmp_path: Path, age_days: int = 0) -> Path:
        fake_dir = Path(tmp_path / "dbdir")
        fake_dir.mkdir(parents=True, exist_ok=True)
        src = fake_dir / "mind.db"
        con = sqlite3.connect(str(src))
        con.execute("CREATE TABLE t1 (x INTEGER)")
        con.execute("INSERT INTO t1 VALUES (1)")
        con.commit()
        con.close()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = fake_dir / f"mind.db.bak-{stamp}"
        shutil.copy2(src, bak)
        if age_days:
            old = time.time() - age_days * 86400
            import os

            os.utime(bak, (old, old))
        return fake_dir

    def test_fresh_and_drilled_is_healthy(self, monkeypatch: Any, tmp_path: Path) -> None:
        fake_dir = self._plant_backup(tmp_path)
        from universal_mind.backup_health import backup_health
        from universal_mind.restore_drill import run_restore_drill

        with patch.object(DatabaseSuite, "DEFAULT_DB_DIR", fake_dir):
            drill = run_restore_drill(fake_dir)
            assert drill.ok is True
            h = backup_health()
            assert h["ok"] is True
            assert "✅" in h["report"]
            assert "مانورِ آخر" in h["report"]    # the drill verdict, read back

    def test_stale_backup_warns_explicitly(self, monkeypatch: Any, tmp_path: Path) -> None:
        fake_dir = self._plant_backup(tmp_path, age_days=10)
        from universal_mind.backup_health import backup_health

        with patch.object(DatabaseSuite, "DEFAULT_DB_DIR", fake_dir):
            h = backup_health()
            assert h["ok"] is False
            assert "کهنه" in h["report"]          # the explicit warning

    def test_missing_backup_says_so_by_name(self, monkeypatch: Any, tmp_path: Path) -> None:
        from universal_mind.backup_health import backup_health

        with patch.object(DatabaseSuite, "DEFAULT_DB_DIR",
                          Path(tmp_path / "empty")):
            h = backup_health()
            assert h["ok"] is False
            assert "هیچ بکاپی" in h["report"]

    def test_speech_answers_the_question(self, monkeypatch: Any, tmp_path: Path) -> None:
        fake_dir = self._plant_backup(tmp_path)
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        with patch.object(DatabaseSuite, "DEFAULT_DB_DIR", fake_dir):
            p = route_and_run("بکاپ سالم است؟")
            assert "بکاپ" in p["agent_report"]
