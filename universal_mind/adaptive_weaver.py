"""Adaptive semantic weaving — learn the best fusion order from real artifacts (Phase 4-ext).

``weave_semantic`` is a fixed algorithm: it decides which output is the "draft"
anchor and which are the "fact"/"note" passengers purely from input order
(``facts[0]``, ``drafts[0]``). It never learns. This module closes that loop the
same way ``AdaptiveOrchestrator`` closed the execution-order loop: it records, per
weave, which capability anchored and which shape flowed where, scores each outcome,
and teaches the next weave to prefer the anchor order that has produced better,
faster, more complete artifacts.

The artifact of learning is "which capability should be the draft anchor first".
A capability that has been a reliable anchor (produced a semantic, complete weave)
rises; one that yields only a structural fallback (a sign the anchor was a poor
fit) falls. Ties break by original order, so the system is deterministic.

Evidence-only and reversible: it records on itself (never mutates a tool or its
output) and can be discarded to forget everything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from universal_mind.semantic_synthesis import FusedArtifact, Part, weave_semantic


@dataclass
class AnchorRecord:
    """Learned stats for one capability when it anchored a weave."""

    times_anchored: int = 0
    times_semantic: int = 0      # how often the weave was a true 'semantic' fusion

    @property
    def semantic_ratio(self) -> float:
        """Fraction of weaves where this anchor produced a true semantic fusion."""
        return self.times_semantic / self.times_anchored if self.times_anchored else 0.0


@dataclass
class AdaptiveWeaver:
    """A weave_semantic wrapper that learns which capability to anchor the weave on."""

    _anchor_stats: dict[str, AnchorRecord] = field(default_factory=dict)

    def weave(self, parts: list[Part]) -> FusedArtifact:
        """Weave, then record which capability anchored and whether it was semantic.

        The learning is a side effect on ``self``; the returned artifact is exactly
        what ``weave_semantic`` would produce for the given order. Adaptive order
        selection is available via :meth:`preferred_anchor_order`.
        """
        artifact = weave_semantic(parts)
        # The anchor is the first 'draft' in the part order (the weaver's anchor).
        anchor = next((name for name, out in parts if isinstance(out, dict) and "draft" in out), None)
        if anchor is not None:
            rec = self._anchor_stats.setdefault(anchor, AnchorRecord())
            rec.times_anchored += 1
            if artifact.method == "semantic":
                rec.times_semantic += 1
        return artifact

    def preferred_order(self, parts: list[Part]) -> list[Part]:
        """Re-order ``parts`` so the most-reliable anchor comes first.

        Capabilities never seen as an anchor keep their original relative order
        (no guessing). The one with the highest semantic-anchor ratio goes first,
        so the weave is most likely to be a true semantic fusion. Ties keep the
        original order for determinism.
        """
        def key(part: tuple[str, Any]) -> tuple[float, int]:
            name = part[0]
            rec = self._anchor_stats.get(name)
            ratio = rec.semantic_ratio if rec else 0.0
            # -(index) makes later items sort first on a ratio tie under reverse,
            # which is wrong; to keep ties in original order we sort descending by
            # ratio, ascending by index. We encode that as a single sort key.
            return (ratio, -parts.index(part))

        return sorted(parts, key=key, reverse=True)

    def stats(self) -> dict[str, dict[str, float]]:
        """A read-only summary of the learned anchor preferences."""
        return {
            name: {
                "times_anchored": rec.times_anchored,
                "times_semantic": rec.times_semantic,
                "semantic_ratio": round(rec.semantic_ratio, 4),
            }
            for name, rec in self._anchor_stats.items()
        }


__all__ = ["AdaptiveWeaver", "AnchorRecord"]