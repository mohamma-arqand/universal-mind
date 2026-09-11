"""Tests for judgment-health self-assessment."""

from __future__ import annotations

import math

from universal_mind.arete.health import assess_judgment_health
from universal_mind.arete.lineage import JudgmentLineage, JudgmentNode
from universal_mind.arete.standard import StandardKeeper
from universal_mind.memory.store import InMemoryStore


def _node(decision: str, excellence: float = 0.8, name: str = "x") -> JudgmentNode:
    return JudgmentNode(
        depth=0,
        contender=name,
        decision=decision,
        reasoning="r",
        excellence=excellence,
        justice=1.0,
    )


def _lineage(nodes: list[JudgmentNode]) -> JudgmentLineage:
    return JudgmentLineage.from_nodes(StandardKeeper(InMemoryStore()), nodes)


def test_insufficient_decisions_is_healthy_by_construction() -> None:
    lin = _lineage([_node("promoted"), _node("promoted")])
    report = assess_judgment_health(lin)
    assert report.unhealthy is False
    assert "insufficient" in report.summary


def test_healthy_lineage_reports_ok() -> None:
    nodes = [_node("promoted", 0.8), _node("promoted", 0.82), _node("promoted", 0.84),
             _node("promoted", 0.86), _node("promoted", 0.88), _node("promoted", 0.9)]
    report = assess_judgment_health(_lineage(nodes))
    assert report.unhealthy is False
    assert report.summary == "judgment looks healthy"


def test_high_defer_rate_is_unhealthy() -> None:
    nodes = [_node("deferred") for _ in range(6)]
    report = assess_judgment_health(_lineage(nodes))
    assert report.unhealthy is True
    assert any(s.name == "defer_rate" and not s.ok for s in report.signals)


def test_declining_excellence_is_unhealthy() -> None:
    # Excellence drops sharply across accepted decisions.
    nodes = [
        _node("promoted", 0.95, "a"),
        _node("promoted", 0.85, "b"),
        _node("promoted", 0.75, "c"),
        _node("promoted", 0.70, "d"),
        _node("promoted", 0.60, "e"),
        _node("promoted", 0.40, "f"),
    ]
    report = assess_judgment_health(_lineage(nodes))
    assert report.unhealthy is True
    assert any(s.name == "excellence_trend" and not s.ok for s in report.signals)


def test_defer_rate_value_is_correct() -> None:
    nodes = [_node("deferred"), _node("promoted"), _node("deferred"),
             _node("promoted"), _node("promoted"), _node("promoted")]
    report = assess_judgment_health(_lineage(nodes))
    defer_signal = next(s for s in report.signals if s.name == "defer_rate")
    assert math.isclose(defer_signal.value, round(2 / 6, 4), abs_tol=1e-9)


def test_excellence_trend_slope_positive_when_rising() -> None:
    nodes = [_node("promoted", 0.8), _node("promoted", 0.85), _node("promoted", 0.9),
             _node("promoted", 0.95), _node("promoted", 1.0), _node("promoted", 1.0)]
    report = assess_judgment_health(_lineage(nodes))
    trend = next(s for s in report.signals if s.name == "excellence_trend")
    assert trend.value > 0


def test_report_is_deterministic() -> None:
    nodes = [_node("deferred") for _ in range(6)]
    a = assess_judgment_health(_lineage(nodes))
    b = assess_judgment_health(_lineage(nodes))
    assert a.summary == b.summary
    assert a.unhealthy == b.unhealthy