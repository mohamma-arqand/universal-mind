"""PowerZero gate: absolute veto authority (highest precedence)."""

from __future__ import annotations

from typing import Any

from universal_mind.core.intent import Intent

from .base import Gate, Verdict


class PowerZero(Gate):
    """PowerZero gate - absolute veto authority.

    Highest precedence (1000). If this gate returns DENY, the pipeline
    stops immediately and no other gates run. Nothing can override.

    The veto rule: implement veto() to return True for absolute veto.
    Default implementation (DefaultPowerZero) vetoes nothing (open by default).
    """

    def __init__(self):
        # Name is fixed - all PowerZero variants are the same gate type
        self._name = "PowerZero"

    @property
    def precedence(self) -> int:
        return 1000  # Not used anymore, but kept for interface compatibility

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: dict[str, Any]) -> Verdict:
        """Evaluate veto. Returns DENY to veto, ALLOW to continue."""
        intent = context.get('intent')
        if intent is None:
            raise ValueError("PowerZero requires 'intent' in context")

        if self.veto(intent):
            return Verdict.DENY
        return Verdict.ALLOW

    def veto(self, intent: Intent) -> bool:
        """Override to implement veto logic.

        Returns True to veto (absolute block), False to allow.
        Default: never veto.
        """
        return False


class DefaultPowerZero(PowerZero):
    """Default PowerZero that never vetoes (open by default)."""

    def veto(self, intent: Intent) -> bool:
        return False


class AlwaysVetoPowerZero(PowerZero):
    """PowerZero that always vetoes (for testing)."""

    def veto(self, intent: Intent) -> bool:
        return True


class ConditionalVetoPowerZero(PowerZero):
    """PowerZero that vetoes based on intent goal."""

    def __init__(
        self,
        veto_goals: list[str],
    ):
        super().__init__()
        self.veto_goals = veto_goals

    def veto(self, intent: Intent) -> bool:
        return intent.goal in self.veto_goals