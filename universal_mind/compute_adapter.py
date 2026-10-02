"""ComputeTool -> Connector adapter (third real effect in the loop)."""

from __future__ import annotations

from typing import Any

from universal_mind.connectors import ConnectorResult
from universal_mind.real_compute import ComputeTool


class ComputeToolConnector:
    """Adapts :class:`ComputeTool` to the ``Connector`` protocol.

    ``params`` drives the expression (defaults to "2 + 2"):
        {"operation": "evaluate", "expression": "3 * 7"}
    """

    def __init__(self, tool: ComputeTool | None = None) -> None:
        self._tool = tool if tool is not None else ComputeTool()

    def connect(self, spec: Any, params: dict[str, Any]) -> ConnectorResult:
        operation = params.get("operation", "evaluate") or "evaluate"
        if operation != "evaluate":
            return ConnectorResult(ok=False, output=None, error=f"unknown operation: {operation!r}")
        # R61-S1 — THE HONEST COMPUTE: a sentence with NO arithmetic shape
        # («قیمت دلار الان چنده؟») must never receive the 2+2 default — a
        # fabricated answer to a knowledge question is the one thing this
        # platform swore never to do. No expression -> a named refusal that
        # names what the sentence actually asked for.
        expression = str(params.get("expression", "") or "").strip()
        if not expression:
            return ConnectorResult(
                ok=False, output=None,
                error="این سوال محاسبه‌ای نیست (عددی در جمله پیدا نکردم) — "
                      "اگر پرسش دانشی است، پاسخش به مدل زبانی زنده نیاز دارد؛ "
                      "اگر محاسبه می‌خواهی، اعداد و عملگر را بگو (مثلا «۵ منهای ۳ چنده؟»)",
            )
        result = self._tool.evaluate(expression=expression)
        if result.get("ok") is not True:
            return ConnectorResult(ok=False, output=None, error=result.get("error", "failed"))
        return ConnectorResult(ok=True, output=result.get("value"))


__all__ = ["ComputeToolConnector"]