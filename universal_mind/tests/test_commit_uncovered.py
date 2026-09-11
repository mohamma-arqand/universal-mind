"""Coverage for MOUTH branches not reached by the existing suite."""

from __future__ import annotations

import pytest

from universal_mind.mouth.commit import ConscientiousMouth, GuardedMouth, InMemoryMouth
from universal_mind.mouth.types import IntentConflict, IntentNeedsClarification


def test_single_word_goal_needs_clarification() -> None:
    mouth = InMemoryMouth()
    # "compute" is one word -> vagueness gate (len < 2)
    with pytest.raises(IntentNeedsClarification):
        mouth.commit("compute", "owner")


def test_no_criteria_raises_clarification() -> None:
    from universal_mind.core.intent import Determinism

    mouth = InMemoryMouth()
    # A custom extractor that returns no criteria exercises the empty-criteria gate.
    mouth = InMemoryMouth(extractor=lambda t: ("summarize the report", [], [], Determinism.STRICT))
    with pytest.raises(IntentNeedsClarification):
        mouth.commit("anything", "owner")


def test_constraints_get_evidence() -> None:
    mouth = InMemoryMouth()
    structured = mouth.commit("summarize the report without losing detail", "owner")
    # the constraint "without losing detail" should carry evidence
    assert "constraints" in structured.field_evidence


def test_no_sentence_goal_fallback() -> None:
    mouth = InMemoryMouth()
    # text has no sentence punctuation -> goal falls back to first-10-words branch
    structured = mouth.commit("summarize this report thoroughly and completely", "owner")
    assert structured.intent.goal


def test_but_clause_contradiction() -> None:
    mouth = InMemoryMouth()
    # "secure but not secure" -> shared meaningful word "secure" -> conflict
    with pytest.raises(IntentConflict):
        mouth.commit("make it secure but not secure when done", "owner")


class _HealthyLoop:
    def healthy(self) -> bool:
        return False  # unhealthy -> caution should be active via healthy() path


def test_caution_active_falls_back_to_healthy_when_no_bar() -> None:
    # A loop with no acceptance_bar attribute but a healthy() method.
    loop = _HealthyLoop()
    mouth = ConscientiousMouth(InMemoryMouth(), loop)
    assert mouth._caution_active() is True


class _NoSignalLoop:
    pass


def test_caution_inactive_when_no_signal_at_all() -> None:
    mouth = ConscientiousMouth(InMemoryMouth(), _NoSignalLoop())
    assert mouth._caution_active() is False


def test_guarded_mouth_defers_benign_input() -> None:
    mouth = GuardedMouth(InMemoryMouth())
    structured = mouth.commit("summarize the report", "owner")
    assert structured.intent.goal == "summarize the report"


def test_guarded_mouth_custom_markers() -> None:
    mouth = GuardedMouth(InMemoryMouth(), markers=("do the forbidden",))
    with pytest.raises(IntentConflict):
        mouth.commit("please do the forbidden thing", "owner")