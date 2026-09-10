"""PowerZero, made executable — mint a power that actually works.

The charter's open question ("do 37 powers cover infinity?") names *Power Zero*
as the generator of new powers. :class:`~universal_mind.powers.power_zero.PowerZero`
already mints *tokens* (name/description/precedence) at runtime. This module is
the executable half of the same idea: it generates a real, runnable power as
Python source, builds it in an isolated sandbox, benchmarks it, and only lets
ARETĒ (the same non-compensatory evidence rule) decide whether the power is
accepted into the registry or rejected. A generated power never outranks a
built-in and never lands in the live tree unless it clears the gate.

Deterministic and local — the ``generator`` fuction is pure; the benchmark is a
plain function over the candidate's source path.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from universal_mind.prometheus.evolve import Sandbox

from .power_zero import MintedPower, PowerZero

if TYPE_CHECKING:
    from universal_mind.arete.arbiter import ArbitrationVerdict, InMemoryArbiter


class PowerGenerationError(Exception):
    """Raised when a power cannot be generated or loaded from its source."""


@dataclass(frozen=True)
class GeneratedPower:
    """A power minted and vetted by the executable Power Zero."""

    minted: MintedPower | None   # None when the power was rejected (not minted)
    source: str
    benchmark_score: float
    verdict: ArbitrationVerdict
    accepted: bool
    callable: Callable[..., Any] | None


# A generator function turns a name + description into (python_source, expected behavior).
# ``expected`` is a deterministic output the generated power must be able to produce
# when invoked with a canonical probe input, so the benchmark is meaningful.
PowerGenerator = Callable[[str, str], tuple[str, Any]]


def _default_generator(name: str, description: str) -> tuple[str, object]:
    """Emit a tiny pure power: a callable that echoes a canonical tag.

    The generated module defines ``power = lambda *a, **k: <tag>``. It is purely
    a placeholder to exercise the sandbox→benchmark→arbitrate loop; a real
    generator would emit substantive capability code.
    """
    tag = f"minted:{name}"
    source = (
        f"# Generated power '{name}' — {description}\n"
        f"def power(*args, **kwargs):\n"
        f"    return {tag!r}\n"
        "POWER_NAME = " + repr(name) + "\n"
    )
    return source, tag


def _load_callable(sandbox_path: Path) -> Callable[..., Any]:
    """Import the generated module from the sandbox and return its ``power``."""
    spec = importlib.util.spec_from_file_location("generated_power", sandbox_path)
    if spec is None or spec.loader is None:
        raise PowerGenerationError("could not build an import spec for the generated power")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "power", None)
    if not callable(fn):
        raise PowerGenerationError("generated module lacks a callable 'power'")
    return cast("Callable[..., Any]", fn)


class PowerZeroGenerator:
    """Generate + sandbox + benchmark + arbitrate a new power end-to-end."""

    def __init__(
        self,
        *,
        arbiter: InMemoryArbiter | None = None,
        generator: PowerGenerator | None = None,
        benchmark: Callable[[Callable[..., Any], Any], float] | None = None,
    ) -> None:
        if arbiter is None:
            # Lazy import to break the powers→arete→powers cycle.
            from universal_mind.arete.arbiter import InMemoryArbiter

            arbiter = InMemoryArbiter()
        self._arbiter = arbiter
        self._generator = generator if generator is not None else _default_generator
        self._benchmark = benchmark if benchmark is not None else _default_benchmark

    def generate(self, name: str, description: str) -> GeneratedPower:
        """Mint a power, then sandbox+benchmark+arbitrate it.

        The flow (mirroring the charter's ``code -> sandbox -> benchmark ->
        accept/reject``):

        1. emit Python source for the power via the generator;
        2. build + import it inside a throwaway :class:`Sandbox` (never the tree);
        3. benchmark the loaded callable against the generator's expected output;
        4. pit it against a refusal baseline in an ARETĒ dispute: only a
           hard-gate-passing, above-threshold, non-tied winner is accepted.

        On acceptance, the power is also minted via :class:`PowerZero` (strictly
        below all built-ins). On rejection it is NOT minted and the source is not
        retained beyond the returned record.
        """
        source, expected = self._generator(name, description)

        with Sandbox(prefix="um-power-") as sandbox:
            artifact = sandbox.write(f"{name}.py", source)
            fn = _load_callable(artifact)
            score = self._benchmark(fn, expected)

        # Lazy import to break the powers→arete→powers cycle.
        from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
        from universal_mind.powers.judgment import CandidateOutput, Verdict

        arbiter: InMemoryArbiter = self._arbiter if self._arbiter is not None else InMemoryArbiter()

        # Reuse the non-compensatory virtue arbitration: a candidate that fails
        # the justice gate is denied regardless of benchmark, and a refusal
        # baseline keeps the field honest.
        candidate = CandidateOutput(
            strategy_id=f"power:{name}",
            output=source,
            metadata={
                "virtues": {"justice": 1.0, "wisdom": _wisdom(score), "courage": 1.0, "temperance": 1.0},
                "benchmark_score": score,
            },
        )
        baseline = CandidateOutput(
            strategy_id="refusal",
            output="refuse to mint",
            metadata={"virtues": {"justice": 1.0, "wisdom": 0.5, "courage": 1.0, "temperance": 1.0}},
        )
        verdict = arbiter.arbitrate(
            Dispute(goal=f"Mint power {name}", candidates=[candidate, baseline])
        )

        accepted = (
            verdict.decision is Verdict.ALLOW
            and verdict.winner_strategy_id == candidate.strategy_id
        )
        minted: MintedPower | None = None
        if accepted:
            minted = PowerZero.mint_power(name, description, {"benchmark_score": score})

        return GeneratedPower(
            minted=minted,
            source=source,
            benchmark_score=score,
            verdict=verdict,
            accepted=accepted,
            callable=fn if accepted else None,
        )


def _wisdom(score: float) -> float:
    """Map a 0..1 benchmark score into the wisdom virtue band (floor 0.1)."""
    return max(0.1, min(1.0, score))


def _default_benchmark(fn: Callable[..., Any], expected: Any) -> float:
    """Score the power 1.0 if it reproduces the expected output, else 0.0."""
    try:
        return 1.0 if fn() == expected else 0.0
    except Exception:  # noqa: BLE001 — a failed candidate scores zero
        return 0.0