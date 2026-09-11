"""Tests for rubric learning — the rubric improves from its own mistakes."""

from __future__ import annotations

from universal_mind.arete.rubric_learning import learn_rubric
from universal_mind.arete.virtue import VirtueWeights


def test_defer_spiral_raises_accept_threshold() -> None:
    learned = learn_rubric(["defer", "defer", "defer", "allow"])
    base = VirtueWeights()
    assert learned.accept_threshold > base.accept_threshold
    assert "defer" in learned.reason


def test_deny_spiral_lowers_accept_threshold() -> None:
    learned = learn_rubric(["deny", "deny", "deny", "allow"])
    base = VirtueWeights()
    assert learned.accept_threshold < base.accept_threshold
    assert "denial" in learned.reason


def test_allow_history_keeps_rubric() -> None:
    learned = learn_rubric(["allow", "allow", "allow"])
    base = VirtueWeights()
    assert learned.accept_threshold == base.accept_threshold
    assert "working" in learned.reason


def test_empty_history_is_neutral() -> None:
    learned = learn_rubric([])
    base = VirtueWeights()
    assert learned.accept_threshold == base.accept_threshold
    assert "no history" in learned.reason


def test_base_rubric_is_not_mutated() -> None:
    base = VirtueWeights()
    original = base.accept_threshold
    learn_rubric(["defer", "defer"], base=base)
    assert base.accept_threshold == original  # frozen, unchanged


def test_learned_rubric_is_a_valid_virtue_weights() -> None:
    learned = learn_rubric(["defer", "defer", "defer"])
    # It must remain a valid, comprehensive VirtueWeights.
    assert learned.weights.total_weight() > 0