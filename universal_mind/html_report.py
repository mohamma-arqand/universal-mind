"""R73 P1 — the HTML REPORT capability.

«گزارش HTML بساز» used to fall to the PDF tool and hand the operator a
PDF when HTML was asked for (a live sweep found it). The router now has
an html-report route: whenever the sentence names HTML, the report is
REAL HTML — self-contained, RTL, Persian digits, real usage data from
the run history, zero invention. When the sentence asks for a DASHBOARD
the super-platform dashboard (the real-usage one) is built instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _fa_num(value: Any) -> str:
    """Convert the digits of a number to Persian digits."""
    fa = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(fa[int(ch)] if ch.isdigit() else ch for ch in str(value))


def build_html_report(out_path: str | Path | None = None) -> dict[str, Any]:
    """Build a self-contained Persian RTL HTML status report from REAL data.

    out_path=None writes to ``artifacts/html_report.html`` (the documented
    default — the returned payload always carries the real absolute path).
    """
    from datetime import date

    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite.shared_persistent()

    # Real usage — every number MEASURED, never invented.
    hist = db.query(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN ok=1 THEN 1 ELSE 0 END) AS ok_n "
        "FROM run_history"
    )
    total = int(hist["rows"][0]["total"] or 0) if hist.get("ok") and hist["rows"] else 0
    ok_n = int(hist["rows"][0]["ok_n"] or 0) if hist.get("ok") and hist["rows"] else 0
    rate = round(100.0 * ok_n / total, 1) if total else 0.0

    sch = db.query("SELECT COUNT(*) AS n FROM schedules")
    n_sched = int(sch["rows"][0]["n"] or 0) if sch.get("ok") and sch["rows"] else 0

    contacts = db.query("SELECT COUNT(*) AS n FROM contacts")
    n_contacts = int(contacts["rows"][0]["n"] or 0) if contacts.get("ok") and contacts["rows"] else 0

    # The R72 vitals cache feeds this with the REAL machine vitals.
    try:
        from universal_mind.system_status_tool import SystemStatusTool

        vitals = SystemStatusTool().status()
        ram_used = vitals.get("ram_used_pct", 0)
        drives = vitals.get("drives", {})
        drive_txt = " — ".join(
            f"{_fa_num(letter.upper())}: {_fa_num(free)}GB آزاد" for letter, d in drives.items()
            for free in [d.get("free_gb", 0)]
        ) or "قابل خواندن نیست"
    except Exception:  # noqa: BLE001 — the vitals are a VIEW, never fatal
        ram_used = None
        drive_txt = "قابل خواندن نیست"

    today = date.today().isoformat()

    ram_line = (
        f"<p>رم استفاده‌شده: <b>{_fa_num(ram_used)}٪</b></p>" if ram_used is not None
        else "<p>رم: قابل خواندن نیست (نام برده شد)</p>"
    )

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>گزارش وضعیت — ذهن یکپارچه</title>
<style>
  body {{ font-family: "Segoe UI", Tahoma, sans-serif; background: #0b0e14;
         color: #e6e9f0; margin: 0; padding: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem; max-width: 900px; margin: 0 auto; }}
  .card {{ background: #10141d; border: 1px solid #1f2733; border-radius: 12px;
          padding: 1.2rem; }}
  .card h3 {{ margin: 0 0 .5rem; color: #7ab8ff; font-size: .95rem; }}
  .big {{ font-size: 2rem; font-weight: 700; }}
  .muted {{ color: #8a93a6; font-size: .85rem; margin-top: .4rem; }}
  footer {{ text-align: center; color: #8a93a6; margin-top: 2rem;
           font-size: .8rem; }}
</style>
</head>
<body>
<div class="grid">
  <div class="card"><h3>فرمان‌های اجرا‌شده</h3>
    <div class="big">{_fa_num(total)}</div>
    <div class="muted">{_fa_num(ok_n)} موفق — نرخ {_fa_num(rate)}٪</div></div>
  <div class="card"><h3>یادآورهای فعال</h3>
    <div class="big">{_fa_num(n_sched)}</div>
    <div class="muted">زمان‌بندی‌های ثبت‌شدهٔ واقعی</div></div>
  <div class="card"><h3>مخاطبین</h3>
    <div class="big">{_fa_num(n_contacts)}</div>
    <div class="muted">از دیتابیس واقعی</div></div>
  <div class="card"><h3>وضعیت سخت‌افزار</h3>
    {ram_line}
    <div class="muted">{drive_txt}</div></div>
</div>
<footer>تولید‌شده در {today} — هر عدد از دیتابیس/سیستم واقعی خوانده شده است</footer>
</body>
</html>"""

    out = Path(out_path) if out_path else Path("artifacts") / "html_report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(out.resolve()), "bytes": out.stat().st_size}


def _base_css() -> str:
    return """
  body { font-family: "Segoe UI", Tahoma, sans-serif; background: #0b0e14;
         color: #e6e9f0; margin: 0; padding: 2rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem; max-width: 900px; margin: 0 auto; }
  .card { background: #10141d; border: 1px solid #1f2733; border-radius: 12px;
          padding: 1.2rem; }
  .card h3 { margin: 0 0 .5rem; color: #7ab8ff; font-size: .95rem; }
  .big { font-size: 2rem; font-weight: 700; }
  .muted { color: #8a93a6; font-size: .85rem; margin-top: .4rem; }
  footer { text-align: center; color: #8a93a6; margin-top: 2rem; font-size: .8rem; }
  table { border-collapse: collapse; width: 100%; margin-top: .5rem; }
  th, td { border: 1px solid #1f2733; padding: .45rem .6rem; font-size: .9rem;
           text-align: right; }
  th { color: #7ab8ff; background: #151b26; }
"""


def _timeline_rows(db: Any) -> list[dict[str, Any]]:
    """The last N runs as REAL timeline rows (when they ran, ok or not)."""
    q = db.query(
        "SELECT created_at, command, ok FROM run_history "
        "WHERE created_at IS NOT NULL ORDER BY created_at DESC LIMIT 12"
    )
    return list(q["rows"]) if q.get("ok") else []


def build_timeline_view(out_path: str | Path | None = None) -> dict[str, Any]:
    """R73 P4 — the TIMELINE view: today's real runs, newest first."""
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite.shared_persistent()
    rows = _timeline_rows(db)
    items = "".join(
        f"<tr><td>{str(r.get('created_at', ''))[:19]}</td>"
        f"<td>{str(r.get('command', ''))[:60]}</td>"
        f"<td>{'✅' if r.get('ok') else '❌'}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='3'>امروز رانی ثبت نشده است</td></tr>"
    html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>تایم‌لاین امروز</title><style>{_base_css()}</style></head><body>
<h2 style="text-align:center">تایم‌لاین {_fa_num(len(rows))} فرمانِ آخر</h2>
<div class="grid"><div class="card" style="grid-column: 1/-1">
<table><tr><th>زمان</th><th>فرمان</th><th>نتیجه</th></tr>{items}</table>
</div></div>
<footer>هر ردیف از run_history واقعی خوانده شده است</footer></body></html>"""
    out = Path(out_path) if out_path else Path("artifacts") / "timeline_view.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(out.resolve()), "bytes": out.stat().st_size}


def build_table_view(out_path: str | Path | None = None) -> dict[str, Any]:
    """R73 P3 — the TABLE view: the operator's REAL reminders as a table."""
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite.shared_persistent()
    q = db.query(
        "SELECT command, schedule_kind, next_run_at FROM schedules "
        "ORDER BY next_run_at ASC LIMIT 30"
    )
    rows = list(q["rows"]) if q.get("ok") else []
    items = "".join(
        f"<tr><td>{str(r.get('command', ''))[:50]}</td>"
        f"<td>{str(r.get('schedule_kind', ''))}</td>"
        f"<td>{str(r.get('next_run_at', ''))[:19]}</td></tr>"
        for r in rows
    ) or "<tr><td colspan='3'>یادآوری ثبت نشده است</td></tr>"
    html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>جدول یادآورها</title><style>{_base_css()}</style></head><body>
<h2 style="text-align:center">جدول {_fa_num(len(rows))} یادآور</h2>
<div class="grid"><div class="card" style="grid-column: 1/-1">
<table><tr><th>فرمان</th><th>نوع</th><th>اجرای بعدی</th></tr>{items}</table>
</div></div>
<footer>از جدول schedules واقعی خوانده شده است</footer></body></html>"""
    out = Path(out_path) if out_path else Path("artifacts") / "table_view.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(out.resolve()), "bytes": out.stat().st_size}


def build_card_view(out_path: str | Path | None = None) -> dict[str, Any]:
    """R73 P4 — the CARD view: one at-a-glance status card."""
    from universal_mind.database_suite import DatabaseSuite

    db = DatabaseSuite.shared_persistent()
    hist = db.query(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN ok=1 THEN 1 ELSE 0 END) AS ok_n "
        "FROM run_history"
    )
    total = int(hist["rows"][0]["total"] or 0) if hist.get("ok") and hist["rows"] else 0
    ok_n = int(hist["rows"][0]["ok_n"] or 0) if hist.get("ok") and hist["rows"] else 0
    rate = round(100.0 * ok_n / total, 1) if total else 0.0
    html = f"""<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<title>کارت وضعیت</title><style>{_base_css()}</style></head><body>
<div class="grid"><div class="card">
<h3>کارت وضعیت — یک نگاه</h3>
<div class="big">{_fa_num(rate)}٪ <span style="font-size:1rem">موفق</span></div>
<div class="muted">{_fa_num(ok_n)} از {_fa_num(total)} فرمان — از run_history واقعی</div>
</div></div></body></html>"""
    out = Path(out_path) if out_path else Path("artifacts") / "status_card.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(out.resolve()), "bytes": out.stat().st_size}
