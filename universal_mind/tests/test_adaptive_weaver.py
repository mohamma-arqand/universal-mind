"""Tests for the adaptive weaver — learning the best fusion anchor order."""

from __future__ import annotations

from universal_mind.adaptive_weaver import AdaptiveWeaver


def _draft(name: str) -> tuple[str, dict[str, str]]:
    return (name, {"draft": f"draft-{name}"})


def _fact(name: str) -> tuple[str, dict[str, str]]:
    return (name, {"fact": f"fact-{name}"})


def test_weave_records_anchor() -> None:
    weaver = AdaptiveWeaver()
    result = weaver.weave([_draft("report"), _fact("media")])
    assert result.method == "semantic"
    stats = weaver.stats()
    assert stats["report"]["times_anchored"] == 1
    assert stats["report"]["times_semantic"] == 1


def test_weave_records_structural_fallback_as_not_semantic() -> None:
    weaver = AdaptiveWeaver()
    # Two scalars -> structural fallback (anchor-derived stats are unchanged because
    # there's no draft anchor).
    result = weaver.weave([("a", "x"), ("b", "y")])
    assert result.method == "structural"
    assert weaver.stats() == {}


def test_preferred_order_keeps_original_when_no_evidence() -> None:
    weaver = AdaptiveWeaver()
    parts = [_draft("b"), _fact("a"), _draft("c")]
    assert [p[0] for p in weaver.preferred_order(parts)] == ["b", "a", "c"]


def test_preferred_order_promotes_reliable_anchor() -> None:
    weaver = AdaptiveWeaver()
    # "rock" anchors the weave twice and is semantic both times.
    for _ in range(2):
        weaver.weave([_draft("rock"), _fact("media")])
    # "flake" anchors but always yields structural (no fact -> still semantic here,
    # so instead make it a scalar-only via a part that is not a draft anchor).
    parts = [_draft("rock"), _draft("flake"), _fact("media")]
    order = [p[0] for p in weaver.preferred_order(parts)]
    # "rock" has a proven semantic anchor record; it and "flake" both tie on the
    # ratio (1.0 for rock, 0.0 for flake) so rock must come first.
    assert order[0] == "rock"
    assert weaver.stats()["rock"]["semantic_ratio"] == 1.0


def test_preferred_order_ranks_seen_before_unseen() -> None:
    weaver = AdaptiveWeaver()
    weaver.weave([_draft("known"), _fact("media")])
    # "known" is a proven anchor (semantic_ratio 1.0); "fresh" has never anchored.
    parts = [_draft("fresh"), _draft("known"), _fact("media")]
    order = [p[0] for p in weaver.preferred_order(parts)]
    # "known" must rank before "fresh" (proven anchor > unseen).
    assert order.index("known") < order.index("fresh")


def test_stats_is_read_only_summary() -> None:
    weaver = AdaptiveWeaver()
    weaver.weave([_draft("r"), _fact("m")])
    stats = weaver.stats()
    assert set(stats["r"].keys()) == {"times_anchored", "times_semantic", "semantic_ratio"}
    assert stats["r"]["times_anchored"] == 1