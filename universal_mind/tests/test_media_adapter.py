"""Tests for the MediaTool -> Connector adapter and the integrated real chain."""

from __future__ import annotations

from universal_mind.media_adapter import MediaToolConnector
from universal_mind.semantic_synthesis import weave_semantic


def test_generate_operation_returns_real_path() -> None:
    conn = MediaToolConnector()
    result = conn.connect({}, {"operation": "generate", "size": "32x32", "color": "red"})
    assert result.ok is True
    assert result.output["path"]
    assert result.output["bytes"] > 0


def test_inspect_operation_returns_real_metadata() -> None:
    conn = MediaToolConnector()
    gen = conn.connect({}, {"operation": "generate", "size": "40x20"})
    assert gen.ok is True
    result = conn.connect({}, {"operation": "inspect", "path": gen.output["path"]})
    assert result.ok is True
    assert result.output["width"] == 40
    assert result.output["height"] == 20


def test_transcode_operation_returns_real_output() -> None:
    conn = MediaToolConnector()
    gen = conn.connect({}, {"operation": "generate"})
    assert gen.ok is True
    result = conn.connect({}, {"operation": "transcode", "path": gen.output["path"], "out_format": "png"})
    assert result.ok is True
    assert result.output["bytes"] > 0


def test_unknown_operation_fails_clean() -> None:
    conn = MediaToolConnector()
    result = conn.connect({}, {"operation": "nonsense"})
    assert result.ok is False
    assert "unknown operation" in result.error


def test_media_output_weaves_into_semantic_synthesis() -> None:
    """The real media effect joins the semantic synthesis: a generated media fact
    folds into a draft, producing ONE artifact (not a stacked list)."""
    conn = MediaToolConnector()
    gen = conn.connect({}, {"operation": "generate", "size": "24x24", "color": "green"})
    assert gen.ok is True

    # The media tool's real output becomes a 'fact' that the weaver folds in.
    fact = {"fact": f"a {gen.output['bytes']}-byte image was produced"}
    draft = {"draft": "The pipeline finished."}
    woven = weave_semantic([("media", fact), ("report", draft)])
    assert woven.method == "semantic"
    assert "image was produced" in woven.artifact
    assert "The pipeline finished" in woven.artifact


def test_media_tool_runs_through_orchestrate_via_connector_factory() -> None:
    """The real media tool is driven through orchestrate (the super-platform's
    many-tools fuser) via an injected connector factory — so a real effect flows
    through the same synthesis path as every other capability."""
    from universal_mind.orchestration import orchestrate
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
        ToolRegistry,
    )

    reg = ToolRegistry()
    # A tool entry whose capability is "media", but whose connector is custom
    # (the MediaToolConnector) rather than mechanism-derived.
    entry = ToolEntry(
        name="ffmpeg-media",
        capability="media",
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
        absorbable=True,
    )
    reg.register(entry)

    def media_factory(tool: object) -> MediaToolConnector:
        from universal_mind.media_adapter import MediaToolConnector
        return MediaToolConnector()

    # The custom connector produces a real file; orchestrate fuses the sub-output.
    # We route "generate" via params through the factory (a single capability).
    # Since orchestrate calls connector.connect(tool.connection, {}), the custom
    # connector defaults to generate on empty params, so we assert a real output.
    syn = orchestrate(reg, ["media"], connector_factory=media_factory)

    # The default composer bundles by capability; the media output is a real path.
    assert syn.ok is True
    # The real effect (a produced file path) is present in the fused bundle.
    assert syn.output["synthesized_from"]["media"] is not None