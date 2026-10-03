"""R73 P1 — the HTML REPORT connector (the 29th real capability)."""

from __future__ import annotations

from typing import Any


class HtmlReportConnector:
    """«گزارش HTML بساز» — a REAL self-contained Persian RTL HTML report.

    A dashboard ask («داشبورد ...») builds the real-usage super-platform
    dashboard; a report ask builds the status report. Both write REAL
    files with MEASURED numbers — never invented.
    """

    def connect(self, spec: Any, params: dict[str, Any]) -> Any:  # noqa: ANN401
        from universal_mind.connectors import ConnectorResult

        p = dict(params or {})
        out_path = p.get("out_path")
        mode = str(p.get("mode", "report"))  # report | dashboard
        if mode == "dashboard":
            from universal_mind.superplatform_dashboard import build_dashboard

            res = build_dashboard(out_path)
        else:
            from universal_mind import html_report as hr

            builders = {
                "report": hr.build_html_report,
                "timeline": hr.build_timeline_view,
                "table": hr.build_table_view,
                "card": hr.build_card_view,
            }
            res = builders.get(mode, hr.build_html_report)(out_path)
        if res.get("ok") is not True:
            return ConnectorResult(ok=False, output=None,
                                   error=str(res.get("error", "failed")))
        return ConnectorResult(ok=True, output={**res, "mode": mode})

    def run(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        out = self.connect(None, dict(params or {}))
        return {"ok": out.ok, "path": (out.output or {}).get("path", ""),
                "bytes": (out.output or {}).get("bytes", 0)}

    def ops(self) -> dict[str, list[str]]:
        return {"html": ["report", "dashboard"]}
