"""Tests: the Task Scheduler tick install — real schtasks, read back.

R41: these tests exercise the REAL machine task. They must leave the tick
INSTALLED at the end — the suite runs on every release and a test-side
uninstall was silently KILLING the production heartbeat (caught live: the
gate's tick probe went dead after every full run).
"""

from __future__ import annotations

from universal_mind.task_install import TASK_NAME, _query, install, uninstall


class TestTickInstall:
    def test_install_creates_a_real_task_and_reads_it_back(self) -> None:
        """The install is a REAL schtasks registration, verified by query —
        a claimed install that cannot be found is not installed."""
        result = install()
        assert result["ok"] is True, result.get("error", "")
        assert result["task"] == TASK_NAME
        # the read-back shows the task really exists in Task Scheduler
        q = _query()
        assert q["ok"] is True
        assert TASK_NAME in q["detail"]

    def test_the_tick_command_is_absolute_and_quoted(self) -> None:
        from universal_mind.task_install import _tick_command

        cmd = _tick_command()
        assert cmd.startswith('"') and '" "' in cmd  # quoted python and script
        assert "scheduler_tick.py" in cmd

    def test_uninstall_is_idempotent_and_leaves_the_tick_installed(self) -> None:
        """Removing twice: the second (missing task) is still a success —
        and the tick is REINSTALLED afterward so the suite never kills the
        production heartbeat."""
        first = uninstall()
        assert first["ok"] is True
        second = uninstall()
        assert second["ok"] is True  # missing task is not an error
        # RESTORE: the heartbeat must survive the test suite.
        restore = install()
        assert restore["ok"] is True, restore.get("error", "")


class TestTickCLI:
    def test_cli_install_and_uninstall(self) -> None:
        from universal_mind.cli import main

        assert main(["install-tick"]) == 0
        assert main(["uninstall-tick"]) == 0
        # RESTORE: never leave the heartbeat dead behind a passing test.
        assert install()["ok"] is True
