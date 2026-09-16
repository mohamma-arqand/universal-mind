"""Tests: contested execution — two chains race, ARETĒ picks the winner."""

from __future__ import annotations

from universal_mind.contested_execution import run_contested


def _fake_runner(payloads: dict[tuple[str, ...], dict[str, object]]) -> object:
    """An injected executor keyed by route — deterministic, no real side effects."""

    def run(route: tuple[str, ...]) -> dict[str, object]:
        return payloads[route]

    return run


class TestContestedExecution:
    def test_single_capability_has_no_contest(self) -> None:
        """One capability → no honest rival → the single route wins un-contested."""
        seen: list[tuple[str, ...]] = []

        def run(route: tuple[str, ...]) -> dict[str, object]:
            seen.append(route)
            return {
                "ok": True, "command": "میانگین", "route": list(route),
                "result": {"data": {"mean": 3.0}},
                "errors": {}, "durations_ms": {"data": 5.0},
            }

        verdict = run_contested("میانگین", ("data",), run)
        assert verdict.contested is False
        assert verdict.winner is not None and verdict.winner.route == ("data",)
        assert seen == [("data",)]  # exactly one run — no wasted work

    def test_two_capabilities_race_and_the_better_one_wins(self) -> None:
        """chart→pdf vs pdf→chart: with the dataflow active only the former can
        embed the image, so its ARETĒ excellence must be higher and it wins."""

        def run(route: tuple[str, ...]) -> dict[str, object]:
            # mirror the REAL engine: pdf first has no chart to embed yet →
            # the persian_report operation honestly refuses («نموداری برای درج نیست»)
            good = route[0] == "chart"
            if good:
                return {
                    "ok": True, "command": "نمودار و گزارش", "route": list(route),
                    "result": {
                        "chart": {"path": "c.png", "bytes": 25000},
                        "pdf": {"path": "r.pdf", "bytes": 61847},
                    },
                    "errors": {}, "durations_ms": {"chart": 10.0, "pdf": 12.0},
                }
            return {
                "ok": False, "command": "نمودار و گزارش", "route": list(route),
                "result": {"pdf": None},
                "errors": {"pdf": "نموداری برای درج نیست — ابتدا نمودار بساز"},
                "durations_ms": {"pdf": 1.0},
            }

        verdict = run_contested("نمودار و گزارش", ("chart", "pdf"), run)
        assert verdict.contested is True
        assert verdict.winner is not None
        assert verdict.winner.route == ("chart", "pdf")
        assert verdict.winner.excellence > (verdict.loser.excellence if verdict.loser else 0.0)
        assert "برنده" in verdict.reasoning

    def test_synthesis_breaks_an_excellence_tie(self) -> None:
        """Equal excellence both ways, but one run FUSED its outputs (flows) —
        the charter's "more than the sum" must win the tie."""

        def run(route: tuple[str, ...]) -> dict[str, object]:
            fused = route == ("chart", "pdf")
            payload = {
                "ok": True, "command": "نمودار و گزارش", "route": list(route),
                "result": {
                    "chart": {"path": "c.png", "bytes": 25000},
                    "pdf": {"path": "r.pdf", "bytes": 61847},
                },
                "errors": {}, "durations_ms": {"chart": 10.0, "pdf": 12.0},
            }
            if fused:
                payload["flows"] = ["chart → pdf (گزارش فارسی با نمودار درونش)"]
            return payload

        verdict = run_contested("نمودار و گزارش", ("chart", "pdf"), run)
        assert verdict.winner is not None
        assert verdict.winner.route == ("chart", "pdf")
        assert "سنتز تعیینکننده" in verdict.reasoning

    def test_disqualified_candidate_loses_even_with_high_excellence(self) -> None:
        """The non-compensatory rule: a disqualified chain never wins."""

        def run(route: tuple[str, ...]) -> dict[str, object]:
            failed = route == ("data", "chart")
            return {
                "ok": not failed, "command": "داده", "route": list(route),
                "result": {} if failed else {"chart": {"path": "x.png", "bytes": 100}},
                "errors": {"data": "boom"} if failed else {},
                "durations_ms": {"data": 1.0, "chart": 1.0},
            }

        verdict = run_contested("داده", ("data", "chart"), run)
        assert verdict.winner is not None
        assert verdict.winner.route == ("chart", "data")

    def test_true_tie_defers_to_the_advised_route(self) -> None:
        """Identical outcomes both ways → the advised route wins, honestly labeled."""

        def run(route: tuple[str, ...]) -> dict[str, object]:
            return {
                "ok": True, "command": "x", "route": list(route),
                "result": {"data": {"mean": 1.0}, "chart": {"path": "p", "bytes": 10}},
                "errors": {}, "durations_ms": {"data": 1.0, "chart": 1.0},
            }

        verdict = run_contested("x", ("data", "chart"), run)
        assert verdict.winner is not None
        assert verdict.winner.route == ("data", "chart")
        assert "تساوی" in verdict.reasoning

    def test_real_persian_command_contested_live(self) -> None:
        """A REAL contest through the real engine: chart→pdf must beat pdf→chart."""
        from universal_mind.persian_router import route_and_run

        def run(route: tuple[str, ...]) -> dict[str, object]:
            return route_and_run(
                "نمودار خطی بساز و گزارشش کن", forced_route=list(route)
            )

        verdict = run_contested("نمودار خطی بساز و گزارشش کن", ("chart", "pdf"), run)
        assert verdict.contested is True
        assert verdict.winner is not None
        assert verdict.winner.route == ("chart", "pdf")  # the dataflow order
        # both real runs are in the ledger for audit
        assert len(verdict.all_entries) == 2
        # the winning pdf genuinely embedded the chart (dataflow active)
        assert verdict.winner.payload["result"]["pdf"]["bytes"] > 20000