"""ArchiveTool -> Connector adapter, plus the second real tool in the loop."""

from __future__ import annotations

from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.real_archive import ArchiveTool


class ArchiveToolConnector:
    """Adapts :class:`ArchiveTool` to the ``Connector`` protocol.

    ``params`` drives the operation (defaults to "compress"):
        {"operation": "compress", "content": "..."}
    """

    def __init__(self, tool: ArchiveTool | None = None) -> None:
        self._tool = tool if tool is not None else ArchiveTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "compress") or "compress"
        if operation != "compress":
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = self._tool.compress(content=params.get("content", "Universal Mind payload"))
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(
            ok=True,
            output={"path": result.get("path"), "bytes": result.get("bytes")},
        )


__all__ = ["ArchiveToolConnector"]