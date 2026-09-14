"""Tests for the NotifyTool and its connector."""

from __future__ import annotations

from universal_mind.notify_adapter import NotifyToolConnector


def test_notify_adapter_returns_shown() -> None:
    # We do not actually open the tray in CI; the adapter returns the parsed result.
    from unittest.mock import patch

    with patch("universal_mind.real_notify.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "shown\n"
        run.return_value.stderr = ""
        conn = NotifyToolConnector()
        result = conn.connect({}, {"operation": "notify", "title": "t", "body": "b"})
    assert result.ok is True
    assert result.output["shown"] is True


def test_notify_adapter_fails_on_missing_powershell() -> None:
    from unittest.mock import patch

    with patch("universal_mind.real_notify.subprocess.run") as run:
        run.side_effect = FileNotFoundError("powershell not found")
        conn = NotifyToolConnector()
        result = conn.connect({}, {"operation": "notify", "title": "t", "body": "b"})
    assert result.ok is False


def test_unknown_operation_is_refused() -> None:
    conn = NotifyToolConnector()
    result = conn.connect({}, {"operation": "nonsense"})
    assert result.ok is False


def test_adapter_default_operation_works() -> None:
    from unittest.mock import patch

    with patch("universal_mind.real_notify.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "shown\n"
        run.return_value.stderr = ""
        result = NotifyToolConnector().connect({}, {})
    assert result.ok is True and result.output["shown"] is True