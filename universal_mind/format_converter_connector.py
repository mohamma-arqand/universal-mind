"""R74 P2 — the FORMAT CONVERTER connector (the 30th real capability)."""

from __future__ import annotations

from typing import Any


class FormatConvertConnector:
    """«فایل X را به CSV/اکسل/JSON تبدیل کن» — a REAL format conversion.

    The source is read (csv/txt/json/xlsx/md), the target is written for
    real; both sides are NAMED. An unconvertible source is refused by
    name — never a crash, never a fabricated table.
    """

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        p = dict(params or {})
        src = str(p.get("path", "")).strip()
        target = str(p.get("target", "")).strip()
        if not src:
            return ConnectorResult(
                ok=False, output=None,
                error="کدام فایل؟ مسیر منبع را بگو — مثلا: فایل D:/data.txt را به CSV تبدیل کن",
            )
        if not target:
            return ConnectorResult(
                ok=False, output=None,
                error="به چه قالبی؟ CSV، اکسل یا JSON را در جمله نام ببر",
            )
        from universal_mind.format_converter import convert_format

        res = convert_format(src, target)
        if not res.get("ok"):
            return ConnectorResult(ok=False, output=None, error=str(res["error"]))
        return ConnectorResult(ok=True, output={k: v for k, v in res.items() if k != "error"})

    def run(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        out = self.connect(None, dict(params or {}))
        return {"ok": out.ok, "error": out.error or "",
                **(out.output or {})}

    def ops(self) -> dict[str, list[str]]:
        return {"convert": ["csv", "xlsx", "json"]}
