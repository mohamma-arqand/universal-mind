"""ClipboardTool -> Connector adapter."""

from __future__ import annotations

from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.real_clipboard import ClipboardTool


class ClipboardToolConnector:
    """Adapts :class:`ClipboardTool` to the ``Connector`` protocol."""

    def __init__(self, tool: ClipboardTool | None = None) -> None:
        self._tool = tool if tool is not None else ClipboardTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "read") or "read"
        if operation == "write":
            return self._write(params.get("text", ""))
        if operation == "read":
            return self._read()
        return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")

    def _read(self) -> ConnectorResult:
        result = self._tool.get_text()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output=result["outcome"])

    def _write(self, text: str) -> ConnectorResult:
        result = self._tool.set_text(str(text))
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output=result["outcome"])


__all__ = ["ClipboardToolConnector"]