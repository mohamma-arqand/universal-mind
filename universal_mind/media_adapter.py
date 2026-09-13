"""MediaTool -> Connector adapter — bring a real media tool into the super-platform.

The super-platform routes every tool through a :class:`~universal_mind.connectors.Connector`
(``connect(spec, params) -> ConnectorResult``), but :class:`~universal_mind.real_media.MediaTool`
is a plain class with named methods (``generate_image``/``inspect``/``transcode``). This
adapter bridges the two: it wraps a ``MediaTool`` and dispatches the requested
``operation`` (from ``params``) to the matching real method, normalizing the result
into a ``ConnectorResult`` so the media tool can be registered in the tool registry
and driven through ``orchestrate`` / ``run_pipeline`` exactly like any other tool.

This is how the real media *effect* joins the rest of the absorption/synthesis loop:
the media tool becomes one more capability the brain can pick, and its real outputs
(paths, metadata) flow into a synthesis via the semantic weaver.
"""

from __future__ import annotations

from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.real_media import MediaTool


class MediaToolConnector:
    """Adapts a :class:`MediaTool` to the ``Connector`` protocol.

    ``params`` drives the operation:
        {"operation": "generate", "size": "64x36", "color": "blue"}
        {"operation": "inspect", "path": "..."}
        {"operation": "transcode", "path": "...", "out_format": "mp4"}

    A missing/unknown operation is a clean not-ok result, never a crash or a
    fabricated artifact — the same fail-safe contract every connector keeps.
    """

    def __init__(self, tool: MediaTool | None = None) -> None:
        self._tool = tool if tool is not None else MediaTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        # An absent operation defaults to "generate" (the tool's primary effect),
        # so it is reachable through orchestrate/pipeline which call connect with
        # no operation in params.
        operation = params.get("operation", "generate") or "generate"
        if operation == "generate":
            result = self._tool.generate_image(
                size=params.get("size", "64x36"),
                color=params.get("color", "blue"),
            )
        elif operation == "inspect":
            result = self._tool.inspect(str(params.get("path", "")))
        elif operation == "transcode":
            result = self._tool.transcode(
                str(params.get("path", "")),
                out_format=params.get("out_format", "mp4"),
            )
        else:
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")

        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        # Normalize: the `output` is the meaningful real result (path or metadata).
        if operation == "inspect":
            output: Any = result.get("meta", {})
        else:
            output = {"path": result.get("path"), "bytes": result.get("bytes")}
        return ConnectorResult(ok=True, output=output)


__all__ = ["MediaToolConnector"]