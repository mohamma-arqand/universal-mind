"""Tests for the MOUTH ⇄ self-awareness bridge (ConscientiousMouth)."""

from __future__ import annotations

import pytest

from universal_mind.arete.standard import StandardKeeper
from universal_mind.core.identity import DEFAULT_OWNER
from universal_mind.core.self_awareness import SelfAwarenessLoop
from universal_mind.memory.store import InMemoryStore
from universal_mind.mouth.commit import ConscientiousMouth, InMemoryMouth
from universal_mind.mouth.types import IntentNeedsClarification


def _loop() -> SelfAwarenessLoop:
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    return SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)


def test_healthy_mouth_defers_exactly() -> None:
    mouth = ConscientiousMouth(InMemoryMouth(), _loop())
    # A short goal that the wrapped mouth would accept is accepted when healthy.
    result = mouth.commit("summarize the topic", "sovereign")
    assert result.intent.goal


def test_unhealthy_mouth_gets_more_careful() -> None:
    loop = _loop()
    # Force the loop unhealthy by tightening past the caution threshold.
    loop.tighten(bar_step=0.1)
    mouth = ConscientiousMouth(InMemoryMouth(), loop, caution_goal_words=5)
    with pytest.raises(IntentNeedsClarification):
        mouth.commit("summarize it", "sovereign")  # 2-word goal -> too short


def test_unhealthy_mouth_still_accepts_full_goals() -> None:
    loop = _loop()
    loop.tighten(bar_step=0.1)
    mouth = ConscientiousMouth(InMemoryMouth(), loop, caution_goal_words=5)
    result = mouth.commit("summarize the topic thoroughly with citations", "sovereign")
    assert result.intent.goal


def test_caution_keyed_to_acceptance_bar() -> None:
    loop = _loop()
    mouth = ConscientiousMouth(InMemoryMouth(), loop)
    # Fresh loop: bar 0.9, below the caution threshold.
    assert mouth._caution_active() is False
    # After a strong tighten, the bar crosses the threshold -> cautious.
    loop.tighten(bar_step=0.1)
    assert mouth._caution_active() is True