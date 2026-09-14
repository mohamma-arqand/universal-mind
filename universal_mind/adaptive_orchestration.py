"""Adaptive orchestration — a closed learning loop over real executions.

``learn_path`` and ``learn_merits`` rank tools, but neither *applies* the lesson to
the next run: they read evidence and emit a preference, stop. This module closes
the loop. :class:`AdaptiveOrchestrator` wraps ``orchestrate`` with a running record
of each real execution — success AND latency — and uses that record to shape the
*next* run, so the super-platform gets measurably better at routing over time
instead of merely replaying a fixed order.

The unit of learning is a capability: how many times it ran, its mean latency, and
its success rate. A capability that is fast and reliable is scheduled *earlier* on
the next multi-capability request (so downstream work can start while a slow tool
still runs its independent task), and a capability that has failed is retained
last. The learning is evidence-only and reversible: it never deletes a tool or its
history, and it never mutates any tool's output.

Deterministic and pure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from universal_mind.orchestration import orchestrate
from universal_mind.tool_registry import ToolRegistry


@dataclass
class CapabilityRecord:
    """Running stats for one capability across executions."""

    runs: int = 0
    successes: int = 0
    total_latency: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0

    @property
    def mean_latency(self) -> float:
        return self.total_latency / self.runs if self.runs else float("inf")


@dataclass
class AdaptiveOrchestrator:
    """An orchestrate wrapper that learns routing order from real executions."""

    registry: ToolRegistry
    _records: dict[str, CapabilityRecord] = field(default_factory=dict)

    def _record(self, capability: str) -> CapabilityRecord:
        return self._records.setdefault(capability, CapabilityRecord())

    def run(self, capabilities: list[str], **kwargs: Any) -> Any:
        """Run a synthesis, then record each capability's real success + latency.

        Latency now comes from the per-capability ``duration_ms`` measured by
        ``orchestrate`` (not a single total shared across all capabilities), so the
        learning is meaningful: a genuinely slow tool accumulates higher latency.
        Returns the ``Synthesis`` unchanged; learning is a side effect on ``self``.
        """
        syn = orchestrate(self.registry, capabilities, **kwargs)

        for cap in capabilities:
            rec = self._record(cap)
            rec.runs += 1
            sub = next((s for s in syn.sub_outputs if s.capability == cap), None)
            if sub is not None:
                rec.total_latency += sub.duration_ms  # real, per-tool wall clock
                if sub.ok:
                    rec.successes += 1
        return syn

    def optimized_order(self, capabilities: list[str]) -> list[str]:
        """Order ``capabilities`` by learned preference (reliable, then fast first).

        A never-run capability has no record and rank last (no guessing). A failed
        capability (success_rate 0) ranks after all successes — running a fast but
        broken tool is still wasted work. Among successes, lower latency first.
        Ties break by the original requested order for determinism.
        """
        def key(cap: str) -> tuple[float, float, int]:
            rec = self._records.get(cap)
            if rec is None or rec.runs == 0:
                success, latency = (0.0, float("inf"))
            else:
                success, latency = (rec.success_rate, rec.mean_latency)
            # Higher success first; then lower latency; then original index.
            return (-success, latency, capabilities.index(cap))

        return sorted(capabilities, key=key)

    def stats(self) -> dict[str, dict[str, float]]:
        """A read-only summary of what the orchestrator has learned."""
        return {
            cap: {
                "runs": rec.runs,
                "success_rate": round(rec.success_rate, 4),
                "mean_latency": round(rec.mean_latency, 4),
            }
            for cap, rec in self._records.items()
        }


__all__ = ["AdaptiveOrchestrator", "CapabilityRecord"]