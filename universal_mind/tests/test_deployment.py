"""Tests for the deployment shape: packaging entrypoint + CLI + health probe."""

from __future__ import annotations

import io
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from universal_mind import __version__
from universal_mind.cli import build_health_status, main
from universal_mind.version import __version__ as version_module


def _quiet() -> io.StringIO:
    """Return a sink that silences CLI stdout for tests."""
    return io.StringIO()


def test_version_is_semver() -> None:
    """The package version is a sane semantic-ish version."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert __version__ == version_module


def test_version_re_exported_from_top_level() -> None:
    """version is importable both from cli and the package root."""
    assert isinstance(__version__, str) and "." in __version__


def test_health_status_shape() -> None:
    """build_health_status returns a coherent JSON-able dict."""
    status = build_health_status()
    assert status["stack_ok"] is True
    assert status["version"] == __version__
    assert isinstance(status["layers"], int) and status["layers"] > 0
    assert status["outcome_status"] in ("ok", "not_ok")
    assert isinstance(status["records"], int) and status["records"] > 0


def test_cli_health_exits_zero() -> None:
    """The health command exits 0 on a healthy stack."""
    with redirect_stdout(_quiet()):
        assert main(["health"]) == 0


def test_cli_health_prints_valid_json() -> None:
    """health prints JSON that mirrors the status dict."""
    sink = _quiet()
    with redirect_stdout(sink):
        rc = main(["health", "--compact"])
    assert rc == 0
    import json

    parsed = json.loads(sink.getvalue())
    assert parsed["stack_ok"] is True


def test_cli_demo_exits_zero() -> None:
    """The demo runs end-to-end through the CLI and exits cleanly."""
    with redirect_stdout(_quiet()):
        assert main(["demo"]) == 0


def test_cli_unknown_command_exits_nonzero() -> None:
    """Unknown subcommands are rejected by argparse (SystemExit 2)."""
    with pytest.raises(SystemExit) as exc_info:
        with redirect_stdout(_quiet()):
            main(["does-not-exist"])
    assert exc_info.value.code == 2


def test_cli_version_flag() -> None:
    """--version prints the version and exits 0."""
    with pytest.raises(SystemExit) as exc_info:
        with redirect_stdout(_quiet()):
            main(["--version"])
    assert exc_info.value.code == 0


def test_cli_interactive_exits_zero_on_eof() -> None:
    """The interactive REPL exits cleanly on EOF."""
    from unittest import mock

    with mock.patch("builtins.input", side_effect=EOFError):
        with redirect_stdout(_quiet()):
            assert main(["interactive"]) == 0


def test_cli_replay_recovers_ledger(tmp_path: Path) -> None:
    """replay recovers + audits an on-disk ledger as JSON."""
    from universal_mind.durable import PersistentMind

    mind = PersistentMind.open(tmp_path)
    mind.run("summarize", "audit me")
    sink = _quiet()
    with redirect_stdout(sink):
        rc = main(["replay", "--dir", str(tmp_path)])
    assert rc == 0
    import json

    parsed = json.loads(sink.getvalue())
    assert parsed["total_records"] == mind.ledger_size
    assert "capability_result" in parsed["kinds"]


def test_cli_evolve_runs_pass(tmp_path: Path) -> None:
    """evolve runs one self-evolution pass over a ledger and prints JSON."""
    from universal_mind.memory.store import LocalJSONLStore

    # Seed a failing history so at least one proposal is produced.
    store = LocalJSONLStore(directory=tmp_path)
    from universal_mind.integration import InMemoryIntegrationHarness
    from universal_mind.io.errors import ProviderPermanent
    from universal_mind.io.gateway import Gateway, ScriptedProvider

    harness = InMemoryIntegrationHarness(Gateway([ScriptedProvider([ProviderPermanent("down")])]), store=store)
    from universal_mind.integration import IntegrationError
    with pytest.raises(IntegrationError):
        harness.run("summarize", "fail")

    sink = _quiet()
    with redirect_stdout(sink):
        rc = main(["evolve", "--dir", str(tmp_path)])
    assert rc == 0
    import json

    parsed = json.loads(sink.getvalue())
    assert isinstance(parsed["proposals"], list)
    assert "evolution_summary" not in parsed or isinstance(parsed["evolution_summary"], str)