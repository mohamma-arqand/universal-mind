"""Inductive generalization — learn a rule from few examples, apply to the unseen.

Memorizing examples is not intelligence; the *generalization* is. This module is
the inductive layer: from a small set of (example → outcome) pairs it derives a
simple, inspectable *rule*, then applies that rule to a novel input and reports
both the prediction and the rule itself — so the mind can say "I inferred this
because X holds, not merely because it looked like the examples".

The reference inducer is deliberately simple and deterministic (an exact-signature
unanimous-outcome rule, no string parsing), so the rule is auditable and the
prediction is never a guess; a richer inducer can be injected later without
changing the contract.

Pure and local: no I/O, no state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Example:
    """One (input, outcome) teaching pair."""

    features: dict[str, Any]
    outcome: Any


@dataclass(frozen=True)
class Generalization:
    """The inferred rule and its application to a novel input."""

    rule: str                             # human-readable statement of the inferred rule
    signatures: dict[tuple[tuple[str, Any], ...], Any] = field(default_factory=dict)  # structured rule
    prediction: Any = None
    confidence: float = 0.0
    matched: bool = False


def induce(examples: list[Example]) -> Generalization | None:
    """Infer a rule from few examples.

    The reference rule: for each distinct feature *signature*, if every example
    sharing that signature has the same outcome, that signature → outcome is a
    unanimous rule. The rule set is exact (no guessing); conflicting signatures
    are simply not rules. Returns None for an empty set or when nothing is
    unanimous.
    """
    if not examples:
        return None

    signatures: dict[tuple[tuple[str, Any], ...], Any] = {}
    conflicting: set[tuple[tuple[str, Any], ...]] = set()
    for ex in examples:
        sig = tuple(sorted((k, repr(v)) for k, v in ex.features.items()))
        if sig in conflicting:
            continue
        if sig in signatures and signatures[sig] != ex.outcome:
            conflicting.add(sig)
            signatures.pop(sig, None)
        else:
            signatures[sig] = ex.outcome

    if not signatures:
        return None

    rule_parts = []
    for sig, outcome in sorted(signatures.items(), key=lambda kv: str(kv[0])):
        desc = ", ".join(f"{k}={v}" for k, v in sig)
        rule_parts.append(f"({desc}) -> {outcome!r}")
    rule = " OR ".join(rule_parts)

    covered = sum(
        1 for ex in examples
        if tuple(sorted((k, repr(v)) for k, v in ex.features.items())) in signatures
    )
    confidence = covered / len(examples)

    return Generalization(rule=rule, signatures=signatures, confidence=confidence)


def apply_rule(generalization: Generalization | None, features: dict[str, Any]) -> Generalization:
    """Apply an induced rule to a novel input, returning the prediction.

    If the novel input's signature exactly matches a unanimous signature, the
    prediction is that outcome (matched=True). Otherwise the rule cannot decide
    and the prediction is None (matched=False) — an honest "I don't know", not a
    guess.
    """
    if generalization is None or not generalization.signatures:
        return Generalization(rule="no rule induced", prediction=None, confidence=0.0, matched=False)

    sig = tuple(sorted((k, repr(v)) for k, v in features.items()))
    outcome = generalization.signatures.get(sig)
    return Generalization(
        rule=generalization.rule,
        signatures=generalization.signatures,
        prediction=outcome,
        confidence=generalization.confidence,
        matched=outcome is not None,
    )