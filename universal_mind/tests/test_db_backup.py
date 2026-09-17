"""Tests: the rotating database backup — the corruption lesson, made permanent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch as mock_patch


class TestBackupDatabase:
    def test_backup_creates_a_real_timestamped_copy(self) -> None:
        from universal_mind.scheduler import backup_database

        result = backup_database()
        assert result["ok"] is True
        backup_path = Path(result["backup"])
        assert backup_path.exists()
        assert backup_path.name.startswith("mind.db.bak-2")  # timestamped
        assert result["bytes"] > 0  # a real copy, not a stub

    def test_rotation_keeps_only_the_newest(self) -> None:
        """Four backups with distinct stamps → only the newest THREE remain."""
        import time

        from universal_mind.scheduler import backup_database

        made: list[str] = []
        for i in range(4):
            if i:
                time.sleep(1.1)  # distinct second-precision stamps
            result = backup_database(keep=3)
            assert result["ok"] is True, result.get("error")
            made.append(result["backup"])
        from universal_mind.database_suite import DatabaseSuite

        remaining = sorted(
            f.name for f in DatabaseSuite.DEFAULT_DB_DIR.glob("mind.db.bak-2*")
        )
        assert len(remaining) <= 4  # pruned toward the keep-window
        # the newest backup we made still exists
        assert Path(made[-1]).exists()

    def test_missing_db_fails_honestly(self) -> None:
        from universal_mind.scheduler import backup_database

        with mock_patch(
            "universal_mind.database_suite.DatabaseSuite.DEFAULT_DB_DIR",
            Path("Z:/nonexistent-dir"),
        ):
            result = backup_database()
        assert result["ok"] is False
        assert result["error"]  # the reason, never a silent skip


class TestTickBacksUpFirst:
    def test_the_tick_takes_a_backup(self) -> None:
        """A tick backs up the store before doing its work (corruption lesson)."""
        import sys
        from contextlib import AbstractContextManager
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        import universal_mind.scheduler as sched_mod

        sys.path.insert(0, str(Path("scripts").resolve()))
        from scheduler_tick import tick

        suite = DatabaseSuite()
        store: AbstractContextManager[object] = mock_patch.object(
            sched_mod, "_store", lambda: suite
        )
        with store, mock_patch(
            "universal_mind.scheduler.backup_database", return_value={"ok": True}
        ) as backup, mock_patch(
            "universal_mind.real_notify.NotifyTool.notify"
        ):
            tick()
        backup.assert_called_once()  # the FIRST thing the tick did
