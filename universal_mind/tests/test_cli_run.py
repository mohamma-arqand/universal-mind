"""Tests for the `universal-mind run` CLI door to the super-platform."""

from __future__ import annotations

import json

from universal_mind.cli import main


def _run_cli(capsys, argv: list[str]) -> tuple[int, dict]:
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out)


def test_run_single_capability_real_stats(capsys) -> None:
    code, payload = _run_cli(capsys, [
        "run", "data", "--params", '{"operation":"stats","data":[2,4,4,4,5,5,7,9]}',
    ])
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["data"]["mean"] == 5.0
    assert payload["durations_ms"]["data"] >= 0.0


def test_run_multi_capability_synthesis(capsys) -> None:
    code, payload = _run_cli(capsys, [
        "run", "anything", "--capabilities", "chart,data",
        "--params", '{"operation":"line","series":{"s":[1,3,2]}}',
    ])
    assert code == 0
    assert payload["ok"] is True
    assert payload["result"]["chart"]["bytes"] > 0
    assert payload["result"]["data"]["mean"] == 5.0


def test_run_unknown_capability_fails_honestly(capsys) -> None:
    code, payload = _run_cli(capsys, ["run", "quantum_gravity"])
    assert code == 1
    assert payload["ok"] is False
    # The unknown capability fails through the mechanism fallback connector —
    # an honest failure, never a fabricated result.
    assert payload["errors"]["quantum_gravity"]
    assert payload["result"] == {}


def test_run_invalid_params_json_fails_clean(capsys) -> None:
    code, payload = _run_cli(capsys, ["run", "data", "--params", "not-json"])
    assert code == 1
    assert payload["ok"] is False
    assert "invalid --params" in payload["error"]


def test_run_database_query_real(capsys) -> None:
    code, payload = _run_cli(capsys, ["run", "database"])  # default catalog query
    assert code == 0
    assert payload["ok"] is True
    assert isinstance(payload["result"]["database"], list)