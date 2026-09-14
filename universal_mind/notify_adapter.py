"""NotifyTool -> Connector adapter (fourth real effect)."""

from __future__ import annotations

from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.real_notify import NotifyTool


class NotifyToolConnector:
    """Adapts :class:`NotifyTool` to the ``Connector`` protocol.

    ``params`` drives the toast:
        {"operation": "notify", "title": "...", "body": "..."}
    """

    def __init__(self, tool: NotifyTool | None = None) -> None:
        self._tool = tool if tool is not None else NotifyTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "notify") or "notify"
        if operation != "notify":
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = self._tool.notify(
            title=params.get("title", "Universal Mind"),
            body=params.get("body", "Task complete"),
        )
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={"shown": result.get("shown")})


__all__ = ["NotifyToolConnector"]