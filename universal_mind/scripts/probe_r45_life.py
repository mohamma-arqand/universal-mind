#!/usr/bin/env python3
"""Probe: R45-16 — one live seed, one life: the platform's whole new face.

The final item of the map: ONE seeded store, ONE pass — the time windows
answer, the reminder registers, the conversation replays, the weekly
letter is written, the status's five signals speak, the advice derives
from real runs, the harvest counts its unknowns — and everything the
operator asked lands in ONE real Persian PDF («زندگیِ این هفته»).
Every claim is a live call; the PDF is a real file with real bytes.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PARENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PARENT))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402
from universal_mind.run_history import RunHistory  # noqa: E402


def main() -> int:
    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe_r45w4.db"))
    RunHistory(db)
    now = dt.datetime.now()
    for back, route, ok, exc in (
        (0, "data", 1, 0.95), (0, "data", 1, 0.9), (1, "pdf", 1, 0.8),
        (2, "chart", 1, 0.7), (5, "data", 0, 0.0),
    ):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('probe-seed','{route}',{ok},{exc},'', '{ts}')"
        )
    checks: list[tuple[str, bool]] = []

    with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
        from universal_mind.persian_router import route_and_run

        q_and_a: list[tuple[str, str]] = []

        p = route_and_run("دیروز چی کار کردی؟")
        q_and_a.append(("پنجرهی زمان", p["agent_report"]))
        checks.append(("دیروز پاسخ گرفت", "فرمان اجرا کردم" in p["agent_report"]))

        p = route_and_run("هر روز ساعت ۸ و نیم یادآور کن کشکول را خلاصه کن")
        q_and_a.append(("یادآور", p["agent_report"]))
        checks.append(("یادآور نیمساعته ثبت شد", "۸:۳۰" in p["agent_report"]))

        from universal_mind.chat_history_store import log_message

        log_message("من", "نمودار فروش را بکش", ok=True)
        log_message("سیستم", "نمودار ساخته شد", ok=True)
        p = route_and_run("آخرین گفتگویمان چه بود؟")
        q_and_a.append(("گفتگو", p["agent_report"].splitlines()[0]))
        checks.append(("گفتگو بازپخش شد", "نمودار فروش را بکش" in p["agent_report"]))

        p = route_and_run("گزارش هفته چطور بود؟")
        q_and_a.append(("نامهی هفته", p["agent_report"]))
        checks.append(("نامهی هفته نوشته شد", "نامهی هفته" in p["agent_report"]))

        p = route_and_run("وضعیت خودت چطور است؟")
        q_and_a.append(("وضعیت", p["agent_report"]))
        checks.append(("پنج سیگنال", all(w in p["agent_report"] for w in (
            "تپش", "رانش کارایی", "بکاپ", "رأیهای تو", "تیم سرخ"))))

        p = route_and_run("پیشنهاد بده")
        q_and_a.append(("پیشنهاد", p["agent_report"]))
        checks.append(("پیشنهادِ واقعی", "«data»" in p["agent_report"]))

        route_and_run("فلانbabایی را باطلا کن")
        p = route_and_run("چه واژههایی را نمیشناسی؟")
        q_and_a.append(("واژههای ناشناخته", p["agent_report"]))
        checks.append(("شکار شمرده شد", "«فلانbabایی»" in p["agent_report"]))

        # THE ONE ARTIFACT: everything above, in ONE real Persian PDF.
        from universal_mind.pdf_suite import PdfSuiteConnector

        rows = "\n".join(
            f"{title}: {text}" for title, text in q_and_a
        )
        connector = PdfSuiteConnector()
        res = connector.connect({}, {
            "operation": "persian_rtl",
            "title": "زندگیِ این هفته — یک seed، یک زندگی",
            "paragraphs": [rows, "هر عددِ این سند از اجرایِ واقعیِ همین probe آمده است."],
        })
        ok_pdf = bool(res.ok and res.output and res.output.get("path"))
        path = str(res.output.get("path", "")) if res.output else ""
        size = 0
        if ok_pdf and path:
            size = Path(path).stat().st_size
        print(f"== the life PDF: ok={ok_pdf} bytes={size}")
        checks.append(("PDF واقعی ساخته شد", ok_pdf and size > 1500))
        print(f"   path: {path}")

    print()
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"R45-W4: {'ALL HOLDS GREEN' if not failed else 'FAILED: ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
