"""Direct coverage for the BoundaryAwareness power."""

from __future__ import annotations

import asyncio
from typing import Any

from universal_mind.core.intent import Determinism, Intent
from universal_mind.powers.boundary import (
    BoundaryInput,
    BoundaryOutput,
    BoundaryResponseType,
    InMemoryBoundaryAwareness,
)


def _intent(goal: str) -> Intent:
    return Intent(
        raw_text=goal,
        goal=goal,
        success_criteria=["ok"],
        constraints=[],
        deadline=None,
        determinism=Determinism.STRICT,
        owner_id="owner",
    )


def _check(b: InMemoryBoundaryAwareness, intent: Any, capability: str | None = None,
           context: dict[str, Any] | None = None) -> BoundaryOutput:
    return asyncio.run(b.check(BoundaryInput(intent=intent, requested_capability=capability, context=context)))


def test_domain_refusal() -> None:
    b = InMemoryBoundaryAwareness()
    out = _check(b, _intent("do some astrology"))
    assert out.allowed is False
    assert out.response_type is BoundaryResponseType.REFUSAL
    assert out.refusal is not None and out.refusal.violated_constraint == "domain_allowlist"


def test_cost_escalation() -> None:
    b = InMemoryBoundaryAwareness(max_cost=10.0)
    out = _check(b, _intent("compute something"), context={"estimated_cost": 100.0})
    assert out.allowed is False
    assert out.response_type is BoundaryResponseType.ESCALATION
    assert out.escalation is not None and out.escalation.required_authority == "budget_approver"


def test_human_required_escalation() -> None:
    b = InMemoryBoundaryAwareness()
    out = _check(b, _intent("compute something"), capability="destructive_deploy", context={})
    assert out.allowed is False
    assert out.response_type is BoundaryResponseType.ESCALATION
    assert out.escalation is not None and out.escalation.required_authority == "human_operator"


def test_allow_when_in_bounds() -> None:
    b = InMemoryBoundaryAwareness()
    out = _check(b, _intent("compute something"), capability="compute", context={})
    assert out.allowed is True
    assert out.metadata == {"domain_checked": True, "cost_checked": True}


def test_custom_domains_and_human_required() -> None:
    b = InMemoryBoundaryAwareness(
        allowed_domains=frozenset({"research"}),
        require_human_for=frozenset({"launch"}),
    )
    # research allowed
    assert _check(b, _intent("research this")).allowed is True
    # launch requires human
    out = _check(b, _intent("research"), capability="launch_rocket")
    assert out.allowed is False
    assert out.escalation is not None and out.escalation.required_authority == "human_operator"


def test_cost_within_limit_and_deferral_unused() -> None:
    b = InMemoryBoundaryAwareness(max_cost=1000.0)
    out = _check(b, _intent("compute"), context={"estimated_cost": 50.0})
    assert out.allowed is True
    # cost==0 and no human-required -> allowed path, no deferral branch used
    assert out.response_type is None