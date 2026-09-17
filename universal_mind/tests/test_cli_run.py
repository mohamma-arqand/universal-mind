"""Tests for the `universal-mind run` CLI door to the super-platform."""

from __future__ import annotations

import json
from typing import Any

from _pytest.capture import CaptureFixture

from universal_mind.cli import main


def _run_cli(capsys: CaptureFixture[str], argv: list[str]) -> tuple[int, dict[str, Any]]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_run_single_capability_real_stats(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, [
        "run", "data", "--params", '{"operation":"stats","data":[2,4,4,4,5,5,7,9]}',
    ])
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["data"]["mean"] == 5.0
    assert payload["durations_ms"]["data"] >= 0.0


def test_run_multi_capability_synthesis(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, [
        "run", "anything", "--capabilities", "chart,data",
        "--params", '{"operation":"line","series":{"s":[1,3,2]}}',
    ])
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["chart"]["bytes"] > 0
    assert payload["result"]["data"]["mean"] == 5.0


def test_run_unknown_capability_fails_honestly(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, ["run", "quantum_gravity"])
    assert code == 1
    assert payload["ok"] is False
    # The unknown capability fails through the mechanism fallback connector —
    # an honest failure, never a fabricated result.
    assert payload["errors"]["quantum_gravity"]
    assert payload["result"] == {}


def test_run_invalid_params_json_fails_clean(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, ["run", "data", "--params", "not-json"])
    assert code == 1
    assert payload["ok"] is False
    assert "invalid --params" in payload["error"]


def test_run_list_shows_every_capability_and_ops(capsys: CaptureFixture[str]) -> None:
    """`run --list` shows every registered capability (13 with speech) + ops."""
    code, payload = _run_cli(capsys, ["run", "--list"])
    assert code == 0
    assert len(payload) == 18
    assert "speech" in payload
    assert "ocr" in payload
    assert "excel" in payload and "webfetch" in payload
    assert "pdfreader" in payload and "screenshot" in payload
    total = sum(len(ops) for ops in payload.values())
    assert total >= 100  # the real surface, honestly counted
    assert payload["data"] and "stats" in payload["data"]


def test_run_without_capability_is_honest(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, ["run"])
    assert code == 1
    assert payload["ok"] is False


def test_run_database_query_real(capsys: CaptureFixture[str]) -> None:
    code, payload = _run_cli(capsys, ["run", "database"])  # default catalog query
    assert code == 0
    assert payload["ok"] is True
    assert isinstance(payload["result"]["database"], list)