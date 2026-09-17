"""Tests: three-way quality-gate arbitration — three candidates, one winner."""

from __future__ import annotations

from typing import Any

from universal_mind.quality_gate import run_with_quality_gate


class TestThreeWayGate:
    def test_three_candidate_chains_race_for_real(self) -> None:
        """A 3-step route: advised + reversed + rotation — all three really run,
        the best REAL verdict ships, every attempt stays in the ledger."""
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            # primary is WEAK (its own pdf step fails) so the gate keeps
            # searching; the reversed candidate is the strong one
            good = route == ("pdf", "chart", "data")
            if good:
                return {
                    "ok": True, "command": "x", "route": list(route),
                    "result": {"data": {"mean": 1.0}, "chart": {"path": "c.png", "bytes": 1},
                               "pdf": {"path": "r.pdf", "bytes": 9999}},
                    "errors": {}, "durations_ms": {"data": 1.0, "chart": 1.0, "pdf": 1.0},
                }
            return {
                "ok": False, "command": "x", "route": list(route),
                "result": {},
                "errors": {"pdf": "نموداری برای درج نیست"},
                "durations_ms": {"pdf": 1.0},
            }

        route = ("data", "chart", "pdf")
        # bar=0.99: no early stop, the gate races ALL THREE candidates.
        outcome = run_with_quality_gate("x", route, runner, bar=0.99)
        # the primary ran (weak), then the reversed WON and the search stopped
        assert len(calls) == 2
        assert len(outcome.attempts) == 2
        # the reversed (producer-first in execution) candidate won, honestly
        assert outcome.shipped.route == ("pdf", "chart", "data")
        assert outcome.repaired is True

    def test_two_step_still_two_candidates(self) -> None:
        """A 2-step route has no honest rotation — two candidates, unchanged."""
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            return {
                "ok": True, "command": "x", "route": list(route),
                "result": {"data": {"mean": 1.0}}, "errors": {}, "durations_ms": {},
            }

        outcome = run_with_quality_gate("x", ("data", "chart"), runner, bar=0.99)
        assert len(calls) == 2  # advised + reversed only
        assert len(outcome.attempts) == 2

    def test_single_capability_never_grows_rivals(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            return {
                "ok": True, "command": "x", "route": list(route),
                "result": {"data": {"mean": 1.0}}, "errors": {}, "durations_ms": {},
            }

        outcome = run_with_quality_gate("x", ("data",), runner, bar=0.5)
        assert len(calls) == 1  # no straw men, ever
        assert outcome.repaired is False

    def test_the_repaired_rotation_can_win(self) -> None:
        """When the advised route is weak but the rotation is strong, the
        rotation ships and the repair is honestly labeled."""
        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            if route == ("pdf", "data", "chart"):  # the rotation is strong
                return {
                    "ok": True, "command": "x", "route": list(route),
                    "result": {"data": {"mean": 1.0}, "chart": {"path": "c", "bytes": 1},
                               "pdf": {"path": "r", "bytes": 9999}},
                    "errors": {}, "durations_ms": {"data": 1.0},
                }
            return {
                "ok": False, "command": "x", "route": list(route),
                "result": {}, "errors": {"pdf": "broken order"},
                "durations_ms": {"pdf": 1.0},
            }

        outcome = run_with_quality_gate(
            "x", ("data", "chart", "pdf"), runner, bar=0.99, max_attempts=3,
        )
        assert outcome.repaired is True
        assert outcome.shipped.route == ("pdf", "data", "chart")
        assert "ترمیم خودکار" in outcome.reasoning
