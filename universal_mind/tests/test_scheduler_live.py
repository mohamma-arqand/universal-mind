"""Tests: the LIVE tick branches (R49 wave 2) — run_due's contest/voice/fail
paths, the rotating backup, and the folder-watcher parser.

Every store-touching test runs against an ISOLATED temp db; `DEFAULT_DB_DIR`
is re-pointed so the backup tests never touch the operator's real mind.db.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any
from contextlib import AbstractContextManager
from pathlib import Path
from unittest.mock import patch as mock_patch

import universal_mind.scheduler as sched_mod
from universal_mind.scheduler import (
    backup_database,
    parse_folder_watcher,
    register,
    run_due,
)


def _isolated() -> AbstractContextManager[object]:
    """Route every store call to ONE fresh temp DatabaseSuite."""
    from universal_mind.database_suite import DatabaseSuite

    suite = DatabaseSuite()
    return mock_patch.object(sched_mod, "_store", lambda: suite)


def _due_in(minutes: int = -1) -> AbstractContextManager[object]:
    """A schedule whose next_due is NOW (the tick fires it immediately)."""
    return _isolated()


class TestRunDueLivePaths:
    def test_a_failing_task_reports_honestly_and_advances_the_clock(self) -> None:
        """One bad task never stops the rest — the failure IS the report."""
        from universal_mind.scheduler import list_schedules

        with _isolated():
            register("هر ۱۵ دقیقه میانگین بگیر")
            with mock_patch(
                "universal_mind.persian_router.route_and_run",
                side_effect=RuntimeError("شبکه قطع شد"),
            ):
                with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
                    result = run_due()
            assert result["count"] == 1  # it fired
            fired = result["fired"][0]
            assert fired.get("ok") is not True  # the failure is honest
            assert "شبکه قطع شد" in json.dumps(fired, ensure_ascii=False)
            # the clock advanced even on failure:
            sched = list_schedules()[0]
            assert sched.last_run != ""

    def test_a_poisoned_goal_is_not_respawned_by_the_tick(self) -> None:
        """«نیشِ» همان گام = ۳+ توقف؛ tick آن را دوباره نمیسازد.

        `_poisoned_goals` returns goal IDs; the tick resolves each ID to its
        goal TEXT and skips the schedule whose `__goal__` text matches.
        """
        from universal_mind.scheduler import list_schedules

        with _isolated():
            register("هر ۱۵ دقیقه هدف: میانگین ۴ و ۶ را حساب کن")
            schedules = list_schedules()
            # the goals table lives in the AGENT loop's schema — seed a real
            # stopped row so the tick's ID→text resolution has something to find:
            from universal_mind.agent_loop import _ensure_goals_table

            db = sched_mod._store()
            _ensure_goals_table(db)
            goal_text = schedules[0].command.removeprefix("__goal__")
            safe = goal_text.replace("'", "''")
            db.execute(
                f"INSERT INTO goals (goal, state) VALUES ('{safe}', 'stopped')"
            )
            row = db.query("SELECT id FROM goals ORDER BY id DESC LIMIT 1")
            goal_id = int(row["rows"][0]["id"]) if row.get("ok") and row["rows"] else 0
            with mock_patch(
                "universal_mind.agent_loop._poisoned_goals",
                return_value=[goal_id],
            ):
                with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
                    result = run_due()
            # the tick SKIPPED the poisoned goal (nothing fired)
            assert result["count"] == 0
            # the clock still advanced (the poison stays visible):
            assert list_schedules()[0].last_run != ""

    def test_a_broken_store_returns_an_honest_error(self) -> None:
        """A locked/corrupt store: the tick names the failure, never crashes."""
        with mock_patch.object(
            sched_mod,
            "_store",
            side_effect=RuntimeError("database disk image is malformed"),
        ):
            result = run_due()
        assert result["ok"] is False
        assert "زمانبندیها ناموفق" in result["error"]


class TestRotatingBackup:
    def _repoint(self, tmp_path: Path) -> AbstractContextManager[object]:
        from universal_mind.database_suite import DatabaseSuite

        return mock_patch.object(DatabaseSuite, "DEFAULT_DB_DIR", tmp_path)

    def test_a_real_backup_verifies_and_rotates(self, tmp_path: Path) -> None:
        (tmp_path / "mind.db").write_bytes(b"")
        conn = sqlite3.connect(str(tmp_path / "mind.db"))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        with self._repoint(tmp_path):
            result = backup_database()
        assert result["ok"] is True
        assert Path(result["backup"]).exists()
        assert result["total_backups"] == 1

    def test_a_missing_store_reports_honestly(self, tmp_path: Path) -> None:
        with self._repoint(tmp_path):
            result = backup_database()
        assert result["ok"] is False
        assert "mind.db does not exist" in result["error"]

    def test_pruning_keeps_only_the_newest(self, tmp_path: Path) -> None:
        (tmp_path / "mind.db").write_bytes(b"")
        conn = sqlite3.connect(str(tmp_path / "mind.db"))
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.commit()
        conn.close()
        for old in ["mind.db.bak-20240101-000000", "mind.db.bak-20240102-000000",
                    "mind.db.bak-20240103-000000", "mind.db.bak-20240104-000000"]:
            (tmp_path / old).write_bytes(b"old")
        with self._repoint(tmp_path):
            result = backup_database(keep=2)
        assert result["ok"] is True
        remaining = sorted(p.name for p in tmp_path.glob("mind.db.bak-*"))
        # _prune runs BEFORE the copy (4 old → keep 2 newest old) AND AFTER
        # the copy (3 files → keep 2), so the oldest TWO generations vanish:
        assert len(remaining) == 2
        assert "mind.db.bak-20240101-000000" not in remaining
        assert "mind.db.bak-20240103-000000" not in remaining

    def test_a_corrupt_source_reports_and_cleans_up(self, tmp_path: Path) -> None:
        """A source that cannot open: honest error, no junk file left."""
        (tmp_path / "mind.db").write_bytes(b"not a database at all" * 100)
        with self._repoint(tmp_path):
            result = backup_database()
        assert result["ok"] is False
        assert result["backups"] == []
        # no half-made junk copy survives:
        junk = [p for p in tmp_path.glob("mind.db.bak-2*") if p.read_bytes() != b"old"]
        assert not junk


class TestFolderWatcherParser:
    def test_an_honest_watcher_sentence_parses(self) -> None:
        import os

        import pytest

        result: dict[str, Any] | None = parse_folder_watcher(
            "هر وقت در پوشهی دسکتاپ فایل جدید آمد، میانگین بگیر"
        )
        if result is None:
            pytest.skip("no real desktop folder in this environment")
        assert result is not None  # skip narrows, but mypy wants the explicit assert
        assert os.path.isdir(result["folder"])
        assert result["action"] == "میانگین بگیر"

    def test_a_non_watcher_sentence_is_none(self) -> None:
        assert parse_folder_watcher("هر روز ساعت ۸ گزارش بده") is None
        assert parse_folder_watcher("میانگین ۱ و ۲ را حساب کن") is None

    def test_a_watcher_without_an_action_is_none(self) -> None:
        assert parse_folder_watcher("هر وقت در پوشهی دسکتاپ فایل جدید آمد") is None


__test__ = True
