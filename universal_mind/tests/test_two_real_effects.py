"""One synthesis over TWO distinct real effects — media + archive in one loop.

This is the strongest demonstration of "more than the sum": two real tools of
completely different kinds (ffmpeg media and gzip archive) are driven through a
single orchestrate call via two connector factories, and their real outputs are
woven into one semantic artifact. Neither tool alone produces the combined result.

Uses the real host binaries (ffmpeg and Python's stdlib gzip), so both paths are
genuine effects on real files.
"""

from __future__ import annotations

from universal_mind.archive_adapter import ArchiveToolConnector
from universal_mind.media_adapter import MediaToolConnector
from universal_mind.orchestration import orchestrate
from universal_mind.semantic_synthesis import weave_semantic
from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(name: str, capability: str) -> ToolEntry:
    return ToolEntry(
        name=name,
        capability=capability,
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
        absorbable=True,
    )


def test_two_real_effects_fuse_into_one_synthesis() -> None:
    reg = ToolRegistry()
    reg.register(_entry("ffmpeg-media", "media"))
    reg.register(_entry("gzip-archive", "archive"))

    def factory(tool: ToolEntry) -> MediaToolConnector | ArchiveToolConnector:
        if tool.capability == "media":
            return MediaToolConnector()
        if tool.capability == "archive":
            return ArchiveToolConnector()
        raise AssertionError(f"unexpected capability: {tool.capability}")

    syn = orchestrate(reg, ["media", "archive"], connector_factory=factory)
    assert syn.ok is True

    media_bytes = syn.output["synthesized_from"]["media"]["bytes"]
    archive_bytes = syn.output["synthesized_from"]["archive"]["bytes"]
    assert media_bytes > 0
    assert archive_bytes > 0

    # Both real effects weave into ONE semantic artifact.
    woven = weave_semantic([
        ("media", {"fact": f"rendered a {media_bytes}-byte image"}),
        ("archive", {"draft": f"compressed a {archive_bytes}-byte archive"}),
    ])
    assert woven.method == "semantic"
    assert "rendered a" in woven.artifact
    assert "compressed a" in woven.artifact