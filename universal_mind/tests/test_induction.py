"""Tests for inductive generalization — learn a rule, apply to the unseen."""

from __future__ import annotations

from universal_mind.demiurge.induction import (
    Example,
    apply_rule,
    induce,
)


def _ex(color: str, shape: str, outcome: str) -> Example:
    return Example(features={"color": color, "shape": shape}, outcome=outcome)


def test_induce_learns_a_unanimous_rule() -> None:
    gen = induce([_ex("red", "round", "apple"), _ex("red", "round", "apple"), _ex("yellow", "long", "banana")])
    assert gen is not None
    assert "apple" in gen.rule
    assert "banana" in gen.rule
    assert gen.confidence == 1.0


def test_apply_rule_to_seen_signature() -> None:
    gen = induce([_ex("red", "round", "apple"), _ex("yellow", "long", "banana")])
    result = apply_rule(gen, {"color": "red", "shape": "round"})
    assert result.prediction == "apple"
    assert result.matched is True


def test_apply_rule_to_unseen_is_honest_unknown() -> None:
    gen = induce([_ex("red", "round", "apple")])
    result = apply_rule(gen, {"color": "green", "shape": "round"})
    assert result.prediction is None
    assert result.matched is False


def test_none_is_legitimate_outcome_and_still_matches() -> None:
    """A unanimous None outcome is a real rule; apply_rule must still match it.

    matched is 'signature present in the rule', NOT 'outcome is not None', so a
    rule that maps a signature to None must report matched=True even though the
    prediction is None (an honest 'no prediction' rule, not an unknown).
    """
    # outcome is a legitimate None (e.g. "no prediction for this signature")
    gen = induce([Example(features={"color": "red"}, outcome=None)])
    assert gen is not None
    result = apply_rule(gen, {"color": "red"})
    assert result.prediction is None
    assert result.matched is True  # signature present, even though outcome is None


def test_conflicting_examples_do_not_form_a_rule() -> None:
    # Same signature, two different outcomes -> not unanimous -> no rule for it.
    gen = induce([_ex("red", "round", "apple"), _ex("red", "round", "tomato")])
    assert gen is None


def test_empty_examples_induce_nothing() -> None:
    assert induce([]) is None


def test_generalization_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    gen = apply_rule(induce([_ex("red", "round", "apple")]), {"color": "red", "shape": "round"})
    try:
        gen.prediction = "x"  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True