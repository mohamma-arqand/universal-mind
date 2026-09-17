"""The screenshot tool — the EIGHTEENTH capability: the platform SEES the screen.

PIL.ImageGrab (the OS-native screen capture) takes a REAL screenshot of the
virtual screen: the platform can now capture what the operator sees, then
analyze it with the existing vision/OCR capabilities.

Honest rules:
- The capture is a REAL PNG on disk (path + bytes + dimensions reported).
- On headless/service contexts where the desktop is unavailable, the failure
  is classified, never fabricated.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from universal_mind.connectors import ConnectorResult


class ScreenshotTool:
    """A real screen capture (PIL.ImageGrab)."""

    name = "screenshot"
    capability = "screenshot"

    OPERATIONS = ("capture",)

    def capture(self, out_dir: str | None = None) -> dict[str, Any]:
        """Capture the full virtual screen to a real PNG."""
        try:
            from PIL import ImageGrab

            image = ImageGrab.grab(all_screens=True)
        except OSError as exc:
            return {"ok": False, "error": f"screen unavailable: {exc}", "path": "", "bytes": 0}
        target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-shot-"))
        target.mkdir(parents=True, exist_ok=True)
        out_path = target / "screen.png"
        image.save(out_path)
        return {
            "ok": True, "path": str(out_path), "bytes": out_path.stat().st_size,
            "width": image.width, "height": image.height, "error": "",
        }


class ScreenshotToolConnector:
    """Adapts :class:`ScreenshotTool` to the ``Connector`` protocol."""

    def __init__(self, tool: ScreenshotTool | None = None) -> None:
        self._tool = tool if tool is not None else ScreenshotTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "capture") or "capture"
        if operation != "capture":
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        result = self._tool.capture()
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output={
            k: v for k, v in result.items() if k not in ("ok", "error")
        })


__all__ = ["ScreenshotTool", "ScreenshotToolConnector"]