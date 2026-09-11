"""Deterministic MOUTH: turn raw speech into an evidence-anchored commitment.

The reference implementation is rule-based and fully deterministic (no LLM, no
I/O, no external provider). It:

1. extracts a goal and success criteria from the raw text, citing the exact
   spans they came from;
2. detects a too-vague request and raises :class:`IntentNeedsClarification`
   instead of silently committing to a near-empty contract;
3. detects self-contradicting constraints and raises :class:`IntentConflict`;
4. returns a :class:`StructuredIntent` whose every committed field carries an
   :class:`~universal_mind.arete.evidence.EvidenceBundle`.

A custom extraction function may be injected later (a real LLM judge behind the
same interface) without changing the commitment contract or its auditability.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from universal_mind.arete.evidence import (
    EvidenceBundle,
    EvidencePoint,
    EvidenceSource,
    EvidenceType,
)
from universal_mind.core.intent import Determinism, Intent
from universal_mind.mouth.types import (
    IntentConflict,
    IntentNeedsClarification,
    StructuredIntent,
)

# Extraction result: a parsed proposal before validation.
ExtractedProposal = tuple[str, list[str], list[str], Determinism]


def _evidence(field: str, citation_span: str, value: Any) -> EvidenceBundle:
    """A single evidence point tying a committed field to its raw-text span."""
    return EvidenceBundle(
        (
            EvidencePoint(
                type_=EvidenceType.CORRECTNESS,
                source=EvidenceSource.HUMAN,
                value=value,
                citation=f"{field} <- {citation_span[:80]!r}",
            ),
        )
    )


def _determinism(raw_text: str) -> Determinism:
    """Derive determinism from explicit keywords (default STRICT)."""
    lowered = raw_text.lower()
    creative_signals = (
        "creative", "explore", "brainstorm", "imagine", "design", "free",
    )
    if any(w in lowered for w in creative_signals):
        return Determinism.CREATIVE
    return Determinism.STRICT


def _split_success_criteria(raw_text: str) -> list[str]:
    """Split possible success criteria out of the raw text.

    Looks for sentences/clauses marked by "must", "should", "need", "when",
    "so that", "until". Returns a list of trimmed criteria (possibly empty).
    """
    import re

    markers = ["must", "should", "need to", "so that", "until", "when", "require"]
    criteria: list[str] = []
    # Sentence-ish split to locate criteria-bearing clauses.
    for clause in re.split(r"[.;\n]", raw_text):
        c = clause.strip()
        if not c:
            continue
        if any(c.lower().lstrip().startswith(m) or m in c.lower() for m in markers):
            criteria.append(c)
    # If no markers, fall back to the goal implication.
    return criteria


@runtime_checkable
class Mouth(Protocol):
    """The input gate: raw speech -> a structured, evidenced commitment."""

    def commit(self, raw_text: str, owner_id: str) -> StructuredIntent:
        """Parse and commit raw speech, or raise a clarification/conflict."""
        ...


class InMemoryMouth:
    """Deterministic, evidence-anchored MOUTH (the input gate)."""

    def __init__(
        self,
        extractor: Callable[[str], ExtractedProposal] | None = None,
    ) -> None:
        self._extractor = extractor

    def commit(self, raw_text: str, owner_id: str) -> StructuredIntent:
        """Parse raw speech into a StructuredIntent, or refuse with a reason.

        Raises:
            IntentNeedsClarification: the request is too vague to commit to.
            IntentConflict: the request contradicts itself.
        """
        if not raw_text or not raw_text.strip():
            raise IntentNeedsClarification(
                ["What would you like me to do?"]
            )

        text = raw_text.strip()
        goal, criteria, constraints, determinism = self._extract(text)

        # --- conflict gate first: a self-contradiction is more specific than
        # vagueness, and must be reported as such ---
        conflict = self._detect_conflict(text)
        if conflict is not None:
            raise IntentConflict(conflict)

        # --- vagueness gate: refuse rather than commit to nothing ---
        if not goal or len(goal.split()) < 2:
            raise IntentNeedsClarification(
                ["What is the single outcome you want? (a clear goal)"]
            )
        # A goal with no action verb is a description, not a commitment.
        if not self._has_action_word(goal):
            raise IntentNeedsClarification(
                ["What should I actually do? (an action verb is missing)"]
            )
        if not criteria:
            raise IntentNeedsClarification(
                ["How will you know it succeeded? (at least one success criterion)"]
            )

        intent = Intent.from_raw(
            raw_text=text,
            goal=goal,
            success_criteria=criteria,
            constraints=constraints,
            deadline=None,
            determinism=determinism,
            owner_id=owner_id,
        )

        field_evidence = {
            "goal": _evidence("goal", goal, goal),
            "success_criteria": _evidence("success_criteria", " ; ".join(criteria), criteria),
            "determinism": _evidence("determinism", text, determinism.value),
        }
        if constraints:
            field_evidence["constraints"] = _evidence("constraints", " ; ".join(constraints), constraints)

        return StructuredIntent(intent=intent, field_evidence=field_evidence)

    # --- extraction (deterministic; injectable for a smarter judge later) ---
    def _extract(self, text: str) -> ExtractedProposal:
        if self._extractor is not None:
            return self._extractor(text)

        import re

        sentences = [s.strip() for s in re.split(r"[.;\n]", text) if s.strip()]
        # Goal: the first sentence, or the first 10 words.
        if sentences:
            goal = sentences[0]
        else:
            goal = " ".join(text.split()[:10])

        criteria = _split_success_criteria(text)
        # If no marker-based criteria, derive one from the goal (a commitment
        # still needs a success signal).
        if not criteria:
            criteria = [f"Complete: {goal}"]

        constraints: list[str] = []
        for marker in ["without", "avoid", "not ", "limit", "cannot", "can't"]:
            for clause in re.split(r"[.;\n]", text):
                c = clause.strip()
                if marker in c.lower():
                    constraints.append(c)

        determinism = _determinism(text)
        return goal, criteria, constraints, determinism

    @staticmethod
    def _has_action_word(goal: str) -> bool:
        """Return True if the goal contains a recognizable action verb."""
        lowered = goal.lower()
        action_verbs = (
            "summarize", "write", "compute", "build", "create", "generate",
            "analyze", "design", "find", "make", "run", "solve", "translate",
            "refactor", "review", "plan", "organize", "explain", "brainstorm",
            "deploy", "test", "fix", "search", "compare", "extract", "count",
            "get", "read", "send", "schedule", "report",
        )
        return any(v in lowered for v in action_verbs)

    @staticmethod
    def _detect_conflict(text: str) -> str | None:
        """Return a conflict description if the text contradicts itself.

        Deterministic: detects explicit "but" reversals within one clause and
        direct opposites (e.g. "strictly X ... freely X").
        """
        lowered = text.lower()
        pairs = [
            ("strictly deterministic", "creative"),
            ("do not proceed", "proceed"),
            ("reversible only", "irreversible"),
        ]
        for left, right in pairs:
            if left in lowered and right in lowered:
                return f"'{left}' conflicts with '{right}'"
        # "A but not A" within a clause.
        import re

        for clause in re.split(r"[.;\n]", text):
            lower = clause.strip().lower()
            if " but " in lower:
                before, after = lower.split(" but ", 1)
                shared = set(before.split()) & set(after.split())
                meaningful = {w for w in shared if len(w) > 3}
                if meaningful:
                    return f"clause contradicts itself: {clause.strip()!r}"
        return None


class ConscientiousMouth:
    """A MOUTH that gets *more careful* when the mind's judgment is unhealthy.

    Wraps another :class:`Mouth` and consults a self-awareness loop: when the
    loop reports unhealthy judgment, this mouth raises a harder bar on vague
    goals — it refuses shorthand goals that a healthy mind would still accept,
    asking for clarification rather than committing on behalf of a drifting
    judge. When the mind is healthy, it defers to the wrapped mouth exactly
    (so a healthy system's behavior is unchanged).
    """

    def __init__(self, inner: Mouth, loop: Any, *, caution_goal_words: int = 4) -> None:
        self._inner = inner
        self._loop = loop
        self._caution_goal_words = caution_goal_words

    def commit(self, raw_text: str, owner_id: str) -> StructuredIntent:
        text = (raw_text or "").strip()
        if self._caution_active():
            # The mind is judging itself unhealthy -> be more careful before
            # committing a short/terse goal.
            first = text.split(".")[0].strip() if text else ""
            word_count = len(first.split())
            if word_count > 0 and word_count < self._caution_goal_words:
                raise IntentNeedsClarification(
                    ["The mind is currently being cautious: please state a fuller goal."]
                )
        return self._inner.commit(raw_text, owner_id)

    def _caution_active(self) -> bool:
        # Caution is a function of the reactive state, not a fresh health query:
        # a raised acceptance bar means self-correction has already fired (the
        # mind judged itself unhealthy), so committing should get more careful.
        bar = getattr(self._loop, "acceptance_bar", None)
        if bar is not None:
            return bool(bar) and bar >= 0.95
        healthy = getattr(self._loop, "healthy", None)
        if callable(healthy):
            result = healthy()
            return not bool(result)
        return False