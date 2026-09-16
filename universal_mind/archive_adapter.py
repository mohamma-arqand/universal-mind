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
        if operation not in ("compress", "compress_files"):
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        if operation == "compress_files":
            result = self._tool.compress_files(files=params.get("files"))
        else:
            result = self._tool.compress(content=params.get("content", "Universal Mind payload"))
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        if operation == "compress_files":
            # carry the archived file list: the evidence of what is inside
            return ConnectorResult(ok=True, output={
                "path": result.get("path"),
                "bytes": result.get("bytes"),
                "archived": result.get("archived", []),
                "skipped": result.get("skipped", []),
            })
        return ConnectorResult(
            ok=True,
            output={"path": result.get("path"), "bytes": result.get("bytes")},
        )


__all__ = ["ArchiveToolConnector"]