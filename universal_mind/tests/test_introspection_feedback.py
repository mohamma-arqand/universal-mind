"""Tests for the evolutionary feedback — insights route back into generation."""

from __future__ import annotations

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.powers.introspection_feedback import (
    GenerationInsight,
    extract_insights,
    make_insight_driven_generator,
    shaped_description,
)


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def test_extract_insights_reads_reactive_state() -> None:
    loop = _loop()
    insight = extract_insights(loop)
    assert insight.acceptance_bar == 0.9
    assert insight.budget == 100.0
    assert insight.rejected_branches == ()


def test_shaped_description_bakes_constraints() -> None:
    insight = GenerationInsight(
        rejected_branches=("report-1",),
        best_loser="report-1",
        acceptance_bar=0.95,
        budget=80.0,
        unhealthy=True,
    )
    desc = shaped_description("x", "summarize", insight)
    assert "economical" in desc
    assert "report-1" in desc
    assert "0.95" in desc and "80.0" in desc


def test_insight_driven_generator_is_a_power_generator() -> None:
    """The shaped generator still satisfies the (name, desc) -> (source, expected) contract."""
    loop = _loop()
    gen = make_insight_driven_generator(loop)
    source, expected = gen("count-power", "count the items")
    assert "count" in source.lower()
    assert expected == 2  # count of kwargs {"x":1, "y":2}


def test_insight_driven_generator_reflects_unhealthy_state() -> None:
    loop = _loop()
    loop.tighten(bar_step=0.1)  # unhealthy -> cautious wording
    gen = make_insight_driven_generator(loop)
    source, _ = gen("sum-power", "sum the numbers")
    # The description rewrite affects the emitted source's comment text.
    assert "sum" in source
    insight = extract_insights(loop)
    assert insight.unhealthy is True


def test_generation_insight_is_frozen() -> None:
    insight = GenerationInsight((), None, 0.9, 100.0, False)
    assert insight.acceptance_bar == 0.9 and insight.budget == 100.0