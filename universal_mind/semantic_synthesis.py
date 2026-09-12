"""Semantic synthesis — weave many tool outputs into one new artifact (Phase 3c).

Phase 3a (structural bundle) and 3b (sequential pipeline) keep outputs *separate*
or *ordered*. Phase 3c makes one indivisible D that none of the tools produced
alone — the "more than the sum" that concatenation can never reach.

The hard part of semantic synthesis is that it needs a *shape-aware* composer:
each tool's output has a kind (a fact, a draft, a metric, a decision), and fusion
means folding those kinds together into a single utterance, not just stacking them.
This module provides exactly that — a composer that recognises a small, explicit
shape vocabulary and weaves the parts into one coherent artifact, with a clear
fallback (and an honest ``method`` tag) when the shapes do not fuse.

Deterministic and local; the composer is a pure function over typed parts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FusedArtifact:
    """The woven artifact plus how (and whether) it was a true fusion."""

    artifact: Any
    method: str            # "semantic" (true weave) or "structural" (honest fallback)
    parts: tuple[str, ...]  # the capability names that contributed (ordered)


# A part is (capability_name, output) as typed by the pipeline.
Part = tuple[str, Any]


def _shape_of(output: Any) -> str:
    """Recognise the explicit shape of a tool output (the fusion vocabulary)."""
    if isinstance(output, dict):
        if "fact" in output:
            return "fact"
        if "draft" in output:
            return "draft"
        if "decision" in output:
            return "decision"
        if "metric" in output:
            return "metric"
        if "value" in output:
            return "value"
        return "map"
    return "scalar"


def _render(output: Any) -> str:
    """Render a tool output to a short canonical string for weaving."""
    if isinstance(output, dict):
        if "fact" in output:
            return str(output["fact"]).strip()
        if "draft" in output:
            return str(output["draft"]).strip()
        if "decision" in output:
            return str(output["decision"]).strip()
        if "metric" in output:
            return str(output["metric"]).strip()
        if "value" in output:
            return str(output["value"]).strip()
        return ", ".join(f"{k}:{v}" for k, v in output.items())
    return str(output)


def weave_semantic(parts: list[Part]) -> FusedArtifact:
    """Weave typed parts into one coherent artifact, or fall back honestly.

    The weave folds a ``fact`` into a ``draft`` (the charter's canonical case) and
    appends ``decision``/``metric``/``scalar`` parts as a reasoned trailing note —
    producing a *single* utterance, not a list. When there is no draft/fact pair to
    anchor the weave (e.g. only scalars), it returns an honest structural fallback
    tagged ``method="structural"`` so callers can tell a true fusion from a join.
    """
    facts: list[str] = []
    drafts: list[str] = []
    notes: list[str] = []
    order: list[str] = []

    for name, output in parts:
        order.append(name)
        shape = _shape_of(output)
        text = _render(output)
        if shape == "fact":
            facts.append(text)
        elif shape == "draft":
            drafts.append(text)
        else:
            notes.append(f"{name}={text}")

    if drafts and facts:
        # True semantic weave: fold the fact(s) into the first draft.
        draft = drafts[0].removesuffix(".")
        fact_clause = "; ".join(f" {f}" for f in facts).strip()
        trailing = (" — " + "; ".join(notes)) if notes else ""
        artifact = f"{draft} ({fact_clause}).{trailing}"
        return FusedArtifact(artifact=artifact, method="semantic", parts=tuple(order))

    if drafts:
        # A draft with no fact is still a single utterance (its own synthesis).
        trailing = (" — " + "; ".join(notes)) if notes else ""
        return FusedArtifact(artifact=drafts[0] + trailing, method="semantic", parts=tuple(order))

    # No draft/fact anchor: honest structural fallback (a real bundle, not a fake weave).
    bundle = {name: output for name, output in parts}
    return FusedArtifact(artifact=bundle, method="structural", parts=tuple(order))


__all__ = ["FusedArtifact", "Part", "weave_semantic"]