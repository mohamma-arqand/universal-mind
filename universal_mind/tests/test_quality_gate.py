"""Tests: the quality gate — weak verdicts trigger real self-repair."""

from __future__ import annotations

from typing import Any

from universal_mind.quality_gate import run_with_quality_gate


def _payload(route: tuple[str, ...], ok: bool = True, big: bool = True) -> dict[str, Any]:
    """A realistic route_and_run-shaped payload (mirrors the real failure shape:
    a failed capability carries NO result entry at all, only an honest error)."""
    if not ok:
        # the real engine: the failed pdf produced nothing, chart never ran
        return {
            "ok": False, "command": "فرمان", "route": list(route),
            "result": {},
            "errors": {"pdf": "نموداری برای درج نیست — ابتدا نمودار بساز"},
            "durations_ms": {"pdf": 1.0},
            "flows": [],
        }
    return {
        "ok": True, "command": "فرمان", "route": list(route),
        "result": {
            "chart": {"path": "c.png", "bytes": 25000},
            "pdf": {"path": "r.pdf", "bytes": 61847 if big else 34772},
        },
        "errors": {},
        "durations_ms": {"chart": 10.0, "pdf": 12.0},
        "flows": ["chart → pdf (سنتز)"] if big else [],
    }


class TestQualityGate:
    def test_strong_primary_passes_untouched(self) -> None:
        """Excellence ≥ bar on the first run → shipped as-is, exactly ONE run."""
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            return _payload(route)

        outcome = run_with_quality_gate("فرمان", ("chart", "pdf"), runner, bar=0.5)
        assert outcome.repaired is False
        assert outcome.shipped.route == ("chart", "pdf")
        assert len(calls) == 1  # no wasted second run of excellent work
        assert "گذشت" in outcome.reasoning

    def test_weak_primary_triggers_the_rival_and_repairs(self) -> None:
        """Primary fails (no chart to embed) → the rival route is really run and
        its better verdict ships — repair through search, honestly labeled."""
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            # only the producer-first order produces a real image-bearing report
            return _payload(route, ok=(route == ("chart", "pdf")))

        outcome = run_with_quality_gate("فرمان", ("pdf", "chart"), runner, bar=0.7)
        assert outcome.repaired is True
        assert outcome.shipped.route == ("chart", "pdf")
        assert len(calls) == 2
        assert "ترمیم خودکار" in outcome.reasoning
        # the failed primary attempt is kept for audit, not hidden
        assert outcome.attempts[0].route == ("pdf", "chart")
        assert outcome.attempts[0].excellence < outcome.shipped.excellence

    def test_all_weak_candidates_ship_best_weak_honestly(self) -> None:
        """Every candidate is weak → the best weak one ships, labeled as weak."""

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            return _payload(route, ok=False, big=False)

        outcome = run_with_quality_gate("فرمان", ("chart", "pdf"), runner, bar=0.9)
        assert outcome.shipped.excellence < 0.9
        assert "نه موفقیت جعلی" in outcome.reasoning

    def test_disqualified_primary_is_never_shipped_over_a_clean_rival(self) -> None:
        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            return _payload(route, ok=(route[0] == "chart"))

        outcome = run_with_quality_gate("فرمان", ("pdf", "chart"), runner, bar=0.5)
        assert outcome.shipped.route == ("chart", "pdf")
        assert outcome.shipped.disqualified is False

    def test_single_capability_gate(self) -> None:
        """A one-capability route has no rival: verdict-only, honest."""
        calls: list[tuple[str, ...]] = []

        def runner(route: tuple[str, ...]) -> dict[str, Any]:
            calls.append(route)
            return _payload(route)

        outcome = run_with_quality_gate("فرمان", ("chart",), runner, bar=0.9)
        assert len(calls) == 1
        assert outcome.repaired is False
