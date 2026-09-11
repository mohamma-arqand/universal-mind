"""Tests for execution budgeting — scarce resource allocated by merit."""

from __future__ import annotations

from universal_mind.layers import Layer
from universal_mind.pantheon.budget import allocate_budget, explain
from universal_mind.pantheon.registry import OrganDescriptor


def _organ(name: str, cost: float, credibility: float, latency: float = 50.0) -> OrganDescriptor:
    # A minimal descriptor: the budgeting only reads name/cost/credibility/latency.
    return OrganDescriptor(
        name=name,
        signature="f(intent, params)",
        cost=cost,
        latency_ms=latency,
        credibility=credibility,
        domains=("general",),
        layer=Layer.GATEWAY,
        dossier=object(),  # type: ignore[arg-type]  # not read by the budgeter
    )


def test_selects_best_value_within_budget() -> None:
    organs = [_organ("cheap-good", 1.0, 0.9), _organ("costly-good", 10.0, 0.9), _organ("bad", 1.0, 0.1)]
    alloc = allocate_budget(organs, budget=5.0)
    assert "cheap-good" in alloc.selected
    assert "costly-good" not in alloc.selected  # too expensive, same credibility
    assert alloc.total_cost <= 5.0


def test_credibility_floor_excludes_low_trust() -> None:
    organs = [_organ("good", 1.0, 0.9), _organ("untrusted", 0.5, 0.05)]
    alloc = allocate_budget(organs, budget=10.0, min_credibility=0.5)
    assert "untrusted" in alloc.dropped
    assert "untrusted" not in alloc.selected


def test_ranking_is_best_value_first() -> None:
    organs = [_organ("low", 5.0, 0.5), _organ("high", 1.0, 0.9)]
    alloc = allocate_budget(organs, budget=10.0)
    # 'high' (0.9/1.0=0.9) beats 'low' (0.5/5.0=0.1).
    assert alloc.ranking[0] == "high"


def test_empty_budget_drops_everything() -> None:
    organs = [_organ("a", 5.0, 0.9)]
    alloc = allocate_budget(organs, budget=1.0)
    assert alloc.selected == ()
    assert "a" in alloc.dropped


def test_deterministic_tiebreak() -> None:
    organs = [_organ("b", 1.0, 0.5), _organ("a", 1.0, 0.5)]
    a = allocate_budget(organs, budget=1.0)
    b = allocate_budget(organs, budget=1.0)
    assert a.selected == b.selected
    assert a.selected == ("a",)  # tie resolves by name


def test_remaining_budget_is_reported() -> None:
    organs = [_organ("a", 3.0, 0.9)]
    alloc = allocate_budget(organs, budget=10.0)
    assert alloc.remaining == 7.0
    assert alloc.total_cost == 3.0


def test_explain_is_human_readable() -> None:
    organs = [_organ("keeper", 2.0, 0.9), _organ("costly", 100.0, 0.9)]
    by_name = {o.name: o for o in organs}
    alloc = allocate_budget(organs, budget=5.0)
    text = explain(alloc, by_name)
    assert "keeper" in text
    assert "costly" in text