"""Tests for true synthesis — A+B+C -> D as a new capability, not a concatenation."""

from __future__ import annotations

from universal_mind.compose import compose, fuse_fact_into_draft
from universal_mind.memory.store import InMemoryStore
from universal_mind.synthesis import (
    FactSpecialist,
    SynthesisEngine,
    WriterSpecialist,
)


def test_fusion_produces_a_new_artifact() -> None:
    """Fact + draft fuse into one indivisible sentence (more than the sum)."""
    out = fuse_fact_into_draft([
        {"fact": "the measured value is 42 units."},
        {"draft": "Final: report."},
    ])
    assert out is not None
    assert "Final: report" in out
    assert "42 units" in out
    # It is one artifact, not a list/join of two.
    assert "\n" not in out


def test_fusion_returns_none_when_shape_does_not_allow() -> None:
    assert fuse_fact_into_draft([{"other": "x"}]) is None
    assert fuse_fact_into_draft([{"draft": "no fact"}]) is None


def test_compose_tags_method() -> None:
    fused = compose([{"fact": "x."}, {"draft": "y."}])
    assert fused.method == "fusion"

    # No fusable shape -> falls back to concat, tagged as such.
    integrated = compose([{"a": 1}, {"b": 2}])
    assert integrated.method == "concat"


def test_compose_is_evidence_anchored() -> None:
    fused = compose([{"fact": "x."}, {"draft": "y."}])
    assert fused.evidence.points
    assert fused.evidence.points[0].citation == "synthesis:fusion"


def test_compose_is_deterministic() -> None:
    a = compose([{"fact": "x."}, {"draft": "y."}])
    b = compose([{"fact": "x."}, {"draft": "y."}])
    assert a.artifact == b.artifact
    assert a.method == b.method


def test_engine_still_runs_with_composer() -> None:
    """The engine composes its successful sub-outputs through the composer."""
    en = SynthesisEngine(InMemoryStore())
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    report = en.run("summarize knowledge then write the result")
    assert report.ok
    assert report.synthesized is not None


def test_engine_fuses_when_composer_injected() -> None:
    """With a composer, the engine produces a fused D (method='fusion')."""
    from universal_mind.compose import fuse_fact_into_draft

    en = SynthesisEngine(InMemoryStore(), composer=fuse_fact_into_draft)
    en.register("facts", FactSpecialist())
    en.register("writer", WriterSpecialist())
    report = en.run("summarize knowledge then write the result")
    assert report.ok
    assert report.method == "fusion"
    # The fused artifact is one sentence, not a newline-joined pair.
    assert "\n" not in str(report.synthesized)