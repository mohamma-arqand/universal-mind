"""Direct coverage for the CLI's uncovered command paths.

The deployment face (cli.py) had its error and alternate command paths (dashboard,
chat --local, cycle, and the health-failure branch) only partially exercised.
These tests drive each one directly.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from universal_mind.cli import main


def _quiet() -> io.StringIO:
    return io.StringIO()


def test_cli_dashboard_writes_html(tmp_path: Path) -> None:
    out = tmp_path / "dash.html"
    with redirect_stdout(_quiet()):
        rc = main(["dashboard", "--out", str(out)])
    assert rc == 0
    assert out.exists() and out.read_text(encoding="utf-8").strip() != ""


def test_cli_cycle_runs_on_durable_ledger(tmp_path: Path) -> None:
    out = tmp_path / "cycle.html"
    with redirect_stdout(_quiet()):
        rc = main(["cycle", "--dir", str(tmp_path), "--out", str(out), "--filename", "ledger.jsonl"])
    assert rc == 0
    assert out.exists()


def test_cli_chat_local_repl_exits_on_eof() -> None:
    from unittest import mock

    with mock.patch("universal_mind.cli.input", side_effect=EOFError):
        with redirect_stdout(_quiet()):
            rc = main(["chat", "--local"])
    assert rc == 0


def test_health_status_failure_is_stack_ok_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """A health failure returns stack_ok=False (never raises)."""
    # Force an inner failure: make the temporary store constructor raise.
    import universal_mind.memory.store as store_mod
    from universal_mind.cli import build_health_status

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("store unavailable")

    monkeypatch.setattr(store_mod, "LocalJSONLStore", _boom)
    status = build_health_status()
    assert status["stack_ok"] is False
    assert status["error"] == "store unavailable"
    assert status["records"] == 0


def test_health_status_recovers_after_failure() -> None:
    """A normal call (no forced failure) is healthy — try branch works."""
    from universal_mind.cli import build_health_status

    assert build_health_status()["stack_ok"] is True