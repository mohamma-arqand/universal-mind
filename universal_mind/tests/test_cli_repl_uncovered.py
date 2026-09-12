"""Coverage for cli.py's REPL loop + interactive preamble branches."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest import mock

from universal_mind.cli import _cmd_interactive, _repl


def _quiet() -> io.StringIO:
    return io.StringIO()


class _Report:
    result_content = "the result"
    arbitration = type("Arb", (), {"winner_strategy_id": "x", "decision": type("D", (), {"value": "ALLOW"})()})()
    proposals: tuple[str, ...] = ("tighten",)


class _Runtime:
    def run(self, goal: str, raw_text: str) -> _Report:
        return _Report()


def test_repl_handles_integration_error_and_continues() -> None:
    from universal_mind.integration import IntegrationError

    class _FailingRuntime:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, goal: str, raw_text: str) -> _Report:
            self.calls += 1
            if self.calls == 1:
                raise IntegrationError("boom")
            return _Report()

    with mock.patch("builtins.input", side_effect=["hello", "bye", EOFError]):
        with redirect_stdout(_quiet()):
            rc = _repl(_FailingRuntime())
    assert rc == 0


def test_repl_prints_result_and_arbitration() -> None:
    with mock.patch("builtins.input", side_effect=["hello", EOFError]):
        sink = _quiet()
        with redirect_stdout(sink):
            rc = _repl(_Runtime())
    assert rc == 0
    out = sink.getvalue()
    assert "result:" in out
    assert "arbitrated winner" in out


def test_cmd_interactive_prefix_best_effort() -> None:
    # interactive spins up the harness + sovereign context; EOF exits cleanly.
    with mock.patch("universal_mind.cli.input", side_effect=EOFError):
        with redirect_stdout(_quiet()):
            rc = _cmd_interactive(mock.Mock())
    assert rc == 0