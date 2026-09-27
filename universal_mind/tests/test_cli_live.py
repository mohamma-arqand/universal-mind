"""Tests: the CLI's LIVE doors (R49 wave 2) — goal, fa (json + report),
fa-contest, health-tick, and the unknown-verb catch-all.

Every test runs the REAL main() with capsys — the printed output IS the
contract (the operator reads exactly this).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from unittest.mock import patch as mock_patch

from _pytest.capture import CaptureFixture

from universal_mind.cli import main


class TestGoalDoor:
    def test_a_bad_goal_sentence_names_the_format(
        self, capsys: CaptureFixture[str]
    ) -> None:
        code = main(["goal", "بدون", "قالب"])
        out = capsys.readouterr().out
        assert code == 1
        payload: dict[str, Any] = json.loads(out)
        assert payload["ok"] is False
        assert "قالب هدف" in payload["error"]

    def test_a_real_goal_runs_step_by_step(
        self, capsys: CaptureFixture[str]
    ) -> None:
        with mock_patch("universal_mind.real_notify.NotifyTool.notify"):
            code = main(["goal", "هدف:", "میانگین", "۴", "و", "۶", "را", "حساب", "کن"])
        out = capsys.readouterr().out
        assert code == 0
        assert "میانگین" in out  # the goal's own report, printed


class TestFaDoor:
    def test_fa_prints_the_persian_report(
        self, capsys: CaptureFixture[str]
    ) -> None:
        code = main(["fa", "میانگین ۱۰ و ۲۰ را حساب کن"])
        out = capsys.readouterr().out
        assert code == 0
        assert "✅" in out
        assert "میانگین" in out  # no English leak in the operator's face

    def test_fa_json_prints_the_payload(
        self, capsys: CaptureFixture[str]
    ) -> None:
        code = main(["fa", "میانگین ۱۰ و ۲۰ را حساب کن", "--json"])
        out = capsys.readouterr().out
        assert code == 0
        payload: dict[str, Any] = json.loads(out)
        assert payload["ok"] is True
        assert payload["result"]["data"]["mean"] == 15.0


class TestFaContestDoor:
    def test_an_unrecognized_command_names_it(
        self, capsys: CaptureFixture[str]
    ) -> None:
        code = main(["fa-contest", "qwerty flux"])
        out = capsys.readouterr().out
        assert code == 1
        assert "هیچ قابلیتی شناخته نشد" in out


class TestHealthTickDoor:
    def test_health_tick_prints_json(
        self, capsys: CaptureFixture[str]
    ) -> None:
        code = main(["health-tick"])
        out = capsys.readouterr().out
        assert code == 0
        payload: dict[str, Any] = json.loads(out)
        assert isinstance(payload, dict)  # the tick's own health, printed


class TestUnknownVerb:
    def test_an_unknown_verb_is_refused_by_argparse(
        self, capsys: CaptureFixture[str]
    ) -> None:
        """An invalid subcommand exits 2 from argparse itself (usage printed)."""
        with pytest.raises(SystemExit) as exc:
            main(["quantum-verb"])
        assert exc.value.code == 2
        assert "invalid choice" in capsys.readouterr().err


__test__ = True
