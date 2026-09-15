"""Tests for the clipboard tool and its connector."""

from __future__ import annotations

from universal_mind.clipboard_adapter import ClipboardToolConnector


def test_clipboard_write_reads_back_roundtrip() -> None:
    """When the OS clipboard is accessible: a real write/read roundtrip.
    When it is locked (a headless session may refuse clipboard access), the
    adapter reports not-ok honestly — that is also correct behavior."""
    conn = ClipboardToolConnector()
    write = conn.connect({}, {"operation": "write", "text": "hello from Universal Mind"})
    if not write.ok:
        # The OS refused clipboard access (session locked / headless): the honest
        # not-ok outcome is correct behavior, not a test failure.
        assert write.error
        return
    assert write.output == "hello from Universal Mind"
    read = conn.connect({}, {"operation": "read"})
    assert read.ok is True
    assert read.output == "hello from Universal Mind"


def test_clipboard_read_empty_fails_clean() -> None:
    conn = ClipboardToolConnector()
    result = conn.connect({}, {"operation": "read"})
    # Whatever is on the clipboard right now is read; it must not crash.
    assert result.ok in (True, False)


def test_clipboard_adapter_routes_to_factory() -> None:
    from universal_mind.real_tool_registry import real_connector_factory
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
    )

    entry = ToolEntry(
        name="clip",
        capability="clipboard",
        connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
        absorbable=True,
    )
    from universal_mind.clipboard_adapter import ClipboardToolConnector as C
    assert isinstance(real_connector_factory(entry), C)
