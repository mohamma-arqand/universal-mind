"""Tests: the tick heartbeat — three real signals, honestly classified."""

from __future__ import annotations


class TestTickHealth:
    def test_three_verdicts_classify_honestly(self) -> None:
        """alive / silent / dead from (task_installed, recent_run)."""
        from unittest.mock import patch as mock_patch

        from universal_mind.task_install import tick_health

        # dead: no task, no evidence
        with mock_patch("universal_mind.task_install._query", lambda: {"ok": False}):
            result = tick_health()
        assert result["verdict"] == "dead"

        # silent: task installed but no recent run in the store
        import tempfile
        from pathlib import Path

        empty = Path(tempfile.mkdtemp(prefix="um-health-")) / "mind.db"
        with mock_patch("universal_mind.task_install._query", lambda: {"ok": True}), \
             mock_patch("universal_mind.database_suite.DatabaseSuite.DEFAULT_DB_DIR", empty.parent):
            result = tick_health()
        assert result["verdict"] == "silent"

        # alive: task installed AND a recent run exists (the live store has one)
        with mock_patch("universal_mind.task_install._query", lambda: {"ok": True}):
            result = tick_health()
        assert result["verdict"] == "alive"
        assert result["signals"]["recent_run"] is True

    def test_the_cli_reports_the_heartbeat(self) -> None:
        from universal_mind.cli import main

        rc = main(["tick-health"])
        assert rc == 0  # a health PROBE reports; only the gate decides
