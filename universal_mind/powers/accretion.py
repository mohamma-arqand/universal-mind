"""AccretiveMemory power: write-once experience → reusable lesson.

Spec concept: The ability to accumulate experiences into reusable lessons
that can be applied to future similar situations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Experience:
    """A single experience record."""
    situation: dict[str, Any]  # Context/features of the situation
    action: str                # What was done
    outcome: dict[str, Any]    # What happened
    success: bool              # Whether it succeeded
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class Lesson:
    """A reusable lesson derived from experiences."""
    pattern: dict[str, Any]    # Generalized pattern from experiences
    recommendation: str        # What to do in similar situations
    confidence: float          # 0.0 to 1.0
    supporting_experiences: list[str]  # IDs of experiences that support this
    domain: str                # Domain this lesson applies to


@dataclass(frozen=True)
class AccretionInput:
    """Input for accreting experiences into lessons."""
    experiences: list[Experience]
    domain: str
    min_support: int = 2  # Minimum experiences to form a lesson


@dataclass(frozen=True)
class AccretionOutput:
    """Output from accretion process."""
    lessons: list[Lesson]
    experiences_processed: int
    lessons_created: int


@runtime_checkable
class AccretiveMemory(Protocol):
    """Protocol for accreting experiences into reusable lessons.

    The AccretiveMemory power transforms write-once experiences into
    generalized, reusable lessons that can guide future decisions.
    """

    async def accrete(self, input: AccretionInput) -> AccretionOutput:
        """Convert experiences into lessons.

        Args:
            input: AccretionInput with experiences, domain, min_support

        Returns:
            AccretionOutput with lessons, counts
        """
        ...


class InMemoryAccretiveMemory:
    """Reference in-memory implementation of AccretiveMemory (no I/O)."""

    def __init__(self) -> None:
        self._experiences: list[Experience] = []
        self._lessons: list[Lesson] = []

    async def accrete(self, input: AccretionInput) -> AccretionOutput:
        # Group experiences by similar situation patterns
        # Simple implementation: group by action type
        by_action: dict[str, list[Experience]] = {}
        for exp in input.experiences:
            by_action.setdefault(exp.action, []).append(exp)

        lessons = []
        lesson_id = 0

        for action, exps in by_action.items():
            if len(exps) < input.min_support:
                continue

            # Calculate success rate
            success_count = sum(1 for e in exps if e.success)
            success_rate = success_count / len(exps)

            if success_rate < 0.5:
                continue  # Not reliable enough

            # Generalize pattern from situation keys
            all_keys: set[str] = set()
            for e in exps:
                all_keys.update(e.situation.keys())

            # Build pattern with most common values
            pattern = {}
            for key in all_keys:
                values = [e.situation.get(key) for e in exps if key in e.situation]
                if values:
                    # Most common value
                    from collections import Counter
                    counter = Counter(str(v) for v in values)
                    pattern[key] = counter.most_common(1)[0][0]

            lesson = Lesson(
                pattern=pattern,
                recommendation=f"When {pattern}, perform {action}",
                confidence=success_rate,
                supporting_experiences=[str(id(e)) for e in exps],
                domain=input.domain,
            )
            lessons.append(lesson)
            lesson_id += 1

        self._lessons.extend(lessons)
        self._experiences.extend(input.experiences)

        return AccretionOutput(
            lessons=lessons,
            experiences_processed=len(input.experiences),
            lessons_created=len(lessons),
        )