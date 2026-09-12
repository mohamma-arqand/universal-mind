"""Tests for the tool registry (super-platform Phase A)."""

from __future__ import annotations

from universal_mind.tool_registry import (
    ConnectionMechanism,
    ToolConnectionSpec,
    ToolEntry,
    ToolRegistry,
)


def _entry(
    name: str, capability: str, mechanism: ConnectionMechanism, absorbable: bool = False
) -> ToolEntry:
    spec = (
        ToolConnectionSpec(mechanism=mechanism, command=name)
        if mechanism is ConnectionMechanism.SUBPROCESS
        else (
            ToolConnectionSpec(mechanism=mechanism, endpoint=f"http://{name}")
            if mechanism is ConnectionMechanism.HTTP
            else ToolConnectionSpec(mechanism=mechanism, prog_id=name)
        )
    )
    return ToolEntry(
        name=name, capability=capability, connection=spec, absorbable=absorbable
    )


def test_registry_indexes_by_capability_not_name() -> None:
    reg = ToolRegistry()
    reg.register(_entry("photoshop-cli", "edit_image", ConnectionMechanism.SUBPROCESS))
    reg.register(
        _entry("gimp", "edit_image", ConnectionMechanism.SUBPROCESS, absorbable=True)
    )
    reg.register(_entry("excel", "spreadsheet", ConnectionMechanism.COM))
    # Three tools, indexed under their capability, not their brand name.
    assert reg.capable("edit_image")
    assert reg.capable("spreadsheet")
    assert not reg.capable("send_email")
    assert len(reg.tools_for("edit_image")) == 2


def test_three_connection_mechanisms_are_supported() -> None:
    reg = ToolRegistry()
    reg.register(_entry("ffmpeg", "transcode", ConnectionMechanism.SUBPROCESS))
    reg.register(_entry("gmail", "send_email", ConnectionMechanism.HTTP))
    reg.register(_entry("excel", "spreadsheet", ConnectionMechanism.COM))
    assert (
        reg.tools_for("transcode")[0].connection_mechanism
        is ConnectionMechanism.SUBPROCESS
    )
    assert (
        reg.tools_for("send_email")[0].connection_mechanism is ConnectionMechanism.HTTP
    )
    assert (
        reg.tools_for("spreadsheet")[0].connection_mechanism is ConnectionMechanism.COM
    )


def test_absorbable_subset_is_correct() -> None:
    reg = ToolRegistry()
    reg.register(
        _entry("proprietary", "edit_image", ConnectionMechanism.COM, absorbable=False)
    )
    reg.register(
        _entry(
            "opensource", "edit_image", ConnectionMechanism.SUBPROCESS, absorbable=True
        )
    )
    absorbable = reg.absorbable_for("edit_image")
    assert [t.name for t in absorbable] == ["opensource"]


def test_best_for_ranks_by_evidence_not_name() -> None:
    reg = ToolRegistry()
    proven = _entry(
        "proven", "edit_image", ConnectionMechanism.SUBPROCESS, absorbable=True
    )
    proven.record_evidence(True, 0.9)
    proven.record_evidence(True, 1.0)
    rookie = _entry("rookie", "edit_image", ConnectionMechanism.HTTP, absorbable=True)
    rookie.record_evidence(True, 0.5)
    reg.register(rookie)
    reg.register(proven)
    best = reg.best_for("edit_image")
    assert best is not None
    assert best.name == "proven"


def test_best_for_returns_none_for_unknown_capability() -> None:
    reg = ToolRegistry()
    assert reg.best_for("gibberish") is None


def test_register_is_idempotent_by_name() -> None:
    reg = ToolRegistry()
    e = _entry("ffmpeg", "transcode", ConnectionMechanism.SUBPROCESS)
    reg.register(e)
    reg.register(e)  # re-registering the same name must not duplicate
    assert len(reg.tools_for("transcode")) == 1


def test_evidence_without_scores_ranks_after_proven() -> None:
    reg = ToolRegistry()
    untested = _entry("untested", "edit_image", ConnectionMechanism.SUBPROCESS)
    proven = _entry("proven", "edit_image", ConnectionMechanism.SUBPROCESS)
    proven.record_evidence(True, 0.7)
    reg.register(untested)
    reg.register(proven)
    # A tool with a proven record outranks one with no evidence at all.
    best = reg.best_for("edit_image")
    assert best is not None
    assert best.name == "proven"
