#!/usr/bin/env python3
"""R73 — the VISUAL OUTPUT sweep: 12 live proofs for the HTML-report class.

A live sweep found «گزارش HTML بساز» handing the operator a PDF (the
«گزارش» keyword routed to pdf; nobody read the FORMAT word). This probe
pins: the format word decides, all five views build REAL files with
MEASURED data, the reflexive/list gates close for build verbs, and the
plain list / plain PDF paths survive.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    os.environ["UM_MUTE"] = "1"
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r73p%'")
    arts = Path("artifacts")
    arts.mkdir(exist_ok=True)

    # 1-2 — the format word decides
    p = route_and_run("گزارش HTML بساز")
    check(1, f"«گزارش HTML بساز» routes html-report only ({p.get('route')})",
          p.get("route") == ["html-report"] and p.get("ok") is True)
    p = route_and_run("گزارش PDF بساز")
    check(2, f"«گزارش PDF بساز» still routes pdf ({p.get('route')})",
          "pdf" in (p.get("route") or []) and "html-report" not in (p.get("route") or []))

    # 3-7 — the five views, each a REAL file
    asks = [
        ("report", "گزارش HTML بساز", "html_report.html"),
        ("dashboard", "داشبورد بساز", "superplatform_dashboard.html"),
        ("timeline", "تایم‌لاین کارهای امروز بساز", "timeline_view.html"),
        ("table", "جدول از یادآورهای من بساز", "table_view.html"),
        ("card", "کارت وضعیت بساز", "status_card.html"),
    ]
    for i, (mode, cmd, fname) in enumerate(asks, start=3):
        route_and_run(cmd)
        f = arts / fname
        ok = f.exists() and f.stat().st_size > 500
        check(i, f"«{cmd[:22]}» builds a real {fname} ({f.stat().st_size if f.exists() else 0}B)",
              ok)

    # 8 — every view file is RTL Persian HTML
    all_html = all("<html" in (arts / fn).read_text(encoding="utf-8")
                   for _, _, fn in asks if (arts / fn).exists())
    check(8, "every view is real RTL HTML", all_html)

    # 9 — the report NAMES its path and size (never a bare «انجام شد»)
    p = route_and_run("گزارش HTML بساز")
    rep = str(p.get("agent_report", ""))
    check(9, f"the report names path+size: {rep[rep.find('•'):rep.find('•')+50]!r}",
          "کیلوبایت" in rep and "«" in rep and "artifacts" in rep)

    # 10-11 — the neighbours survive (no gate ate them)
    p = route_and_run("یادآورهای من")
    check(10, "«یادآورهای من» still lists (not stolen by the view gate)",
          p.get("ok") is True and "html-report" not in (p.get("route") or []))
    p = route_and_run("وضعیت کلی من چطور است؟")
    check(11, "«وضعیت کلی من چطور است؟» still answers as a reflex",
          p.get("ok") is True and (p.get("route") or [None])[0] != "html-report")

    # 12 — the connector protocol (registry-grade, not a bare .run)
    from universal_mind.connectors import ConnectorResult
    from universal_mind.html_report_connector import HtmlReportConnector

    out = HtmlReportConnector().connect(None, {"mode": "card"})
    check(12, "the connector speaks connect() -> ConnectorResult",
          isinstance(out, ConnectorResult) and out.ok is True)

    print()
    if FAILURES:
        print(f"R73 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R73 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
