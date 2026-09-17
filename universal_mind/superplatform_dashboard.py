"""Super-platform dashboard — the operator's real usage, one self-contained Persian HTML.

Renders the ACTUAL recorded state of the platform into a single static page:
- usage over time (runs per day, from run_history)
- the most-used chains and capabilities (real counts)
- ARETĒ's mean excellence and the per-capability success rates
- what the planner has LEARNED (the earned needs table)
- the quality-gate repair rate (how often judgment changed behavior)

Nothing fabricated: every number is a SQL query over the persistent store.
The artifact is fully static (open in any browser, no server, no CDN).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from universal_mind.database_suite import DatabaseSuite
from universal_mind.history_analytics import HistoryAnalytics, analyze_history


def _persian_digits(text: str) -> str:
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


_CAP_FA: dict[str, str] = {
    "data": "تحلیل داده", "ai": "یادگیری ماشین", "vision": "بینایی کامپیوتر",
    "chart": "نمودار", "pdf": "سند PDF", "database": "دیتابیس",
    "image": "پردازش تصویر", "media": "رسانه", "archive": "بایگانی",
    "compute": "محاسبه", "notify": "اطلاعرسانی", "clipboard": "کلیپبورد",
}


def _daily_runs(db: DatabaseSuite, days: int = 14) -> list[dict[str, Any]]:
    """Real runs per day (last N days), oldest first."""
    q = db.query(
        "SELECT date(created_at) AS d, COUNT(*) AS n FROM run_history "
        "WHERE created_at IS NOT NULL "
        f"GROUP BY d ORDER BY d DESC LIMIT {days}"
    )
    if not q.get("ok"):
        return []
    rows = list(reversed(q["rows"]))  # oldest first for the chart
    return [{"day": str(r["d"]), "runs": int(r["n"])} for r in rows]


def build_dashboard(out_path: str | None = None) -> dict[str, Any]:
    """Render the real-usage dashboard HTML; returns ok/path/bytes."""
    db = DatabaseSuite(persistent=True)
    stats: HistoryAnalytics = analyze_history()

    # The planner's earned table (proven operations only).
    try:
        from universal_mind.planner_learning import lessons_report

        lessons = [
            l for l in lessons_report()["lessons"] if l["mean_excellence"] >= 0.75
        ]
    except Exception:  # noqa: BLE001 — the lens is a view, never fatal
        lessons = []

    daily = _daily_runs(db)

    # The excellence TREND: mean ARETĒ verdict per day (the learning curve).
    try:
        trend_q = db.query(
            "SELECT date(created_at) AS d, AVG(excellence) AS m FROM run_history "
            "WHERE excellence IS NOT NULL AND succeeded = 1 "
            "GROUP BY d ORDER BY d DESC LIMIT 14"
        )
        trend = list(reversed(trend_q["rows"])) if trend_q.get("ok") else []
    except Exception:  # noqa: BLE001 — a view, never fatal
        trend = []

    # The AGENT's goals: the proactive objectives and where they stand.
    try:
        from universal_mind.agent_loop import _ensure_goals_table

        _ensure_goals_table(db)
        goals_q = db.query(
            "SELECT goal, next_step, state, outcomes FROM goals ORDER BY id DESC LIMIT 8"
        )
        goals_rows = goals_q["rows"] if goals_q.get("ok") else []
    except Exception:  # noqa: BLE001
        goals_rows = []

    # The CROWN: the currently-standing standard chain (the ARETĒ-elected best).
    try:
        from universal_mind.history_analytics import crown_standing_chain

        crown = crown_standing_chain()
        crown_html = (
            f"'{crown['chain']}' با {_persian_digits(str(crown['wins']))} برد "
            f"و داوری {_persian_digits(str(round(crown['mean_excellence'] * 100)))}٪"
            if crown.get("ok") and crown.get("crowned")
            else "هنوز زنجیرهای سزاوارِ تاج نشده"
        )
    except Exception:  # noqa: BLE001
        crown_html = "—"

    # The proactive layer: the operator's real schedules (what runs itself).
    try:
        from universal_mind.scheduler import list_schedules, list_watchers

        schedules = list_schedules()
        watchers = list_watchers()
    except Exception:  # noqa: BLE001 — a view, never fatal
        schedules = []
        watchers = []

    cap_rows = "".join(
        f"<tr><td>{_CAP_FA.get(cap, cap)}</td><td>{_persian_digits(str(count))}</td>"
        f"<td>{_persian_digits(str(round(stats.per_capability_success.get(cap, 0.0) * 100)))}٪</td></tr>"
        for cap, count in stats.top_capabilities
    )
    schedule_rows = "".join(
        f"<tr><td>{s.command}</td>"
        f"<td>{_persian_digits(str(s.every_minutes))} دقیقه</td>"
        f"<td>{'فعال' if s.active else 'غیرفعال'}</td>"
        f"<td>{_persian_digits(s.last_run[:16]) or '—'}</td></tr>"
        for s in schedules
    ) or "<tr><td colspan='4'>هنوز زمانبندیای ثبت نشده</td></tr>"
    trend_rows = "".join(
        f"<tr><td dir='ltr'>{t['d']}</td><td>{_persian_digits(str(round(float(t['m'] or 0) * 100)))}٪</td></tr>"
        for t in trend
    ) or "<tr><td colspan='2'>هنوز داوریای ثبت نشده</td></tr>"
    def _verdict(outcomes_raw: str) -> str:
        import json

        try:
            outcomes = json.loads(outcomes_raw or "[]")
            last = outcomes[-1]["excellence"] if outcomes else None
            return _persian_digits(str(round(float(last) * 100))) + "٪" if last is not None else "—"
        except (ValueError, KeyError, IndexError, TypeError):
            return "—"

    agent_rows = "".join(
        f"<tr><td>{g['goal']}</td><td>{_persian_digits(str(g['next_step']))}</td>"
        f"<td>{_verdict(g.get('outcomes', ''))}</td>"
        f"<td>{'✅ تمام' if g['state'] == 'done' else ('⏸ متوقف' if g['state'] == 'stopped' else '▶ فعال')}</td></tr>"
        for g in goals_rows
    ) or "<tr><td colspan='4'>هدفی ثبت نشده</td></tr>"
    watcher_rows = "".join(
        f"<tr><td dir='ltr'>{w['folder']}</td>"
        f"<td>{w['action']}</td>"
        f"<td>{'فعال' if w['active'] else 'غیرفعال'}</td></tr>"
        for w in watchers
    ) or "<tr><td colspan='3'>پوشهای تحت نظر نیست</td></tr>"
    chain_rows = "".join(
        f"<tr><td dir='ltr'>{chain}</td><td>{_persian_digits(str(count))}</td></tr>"
        for chain, count in stats.top_chains
    )
    lesson_rows = "".join(
        f"<tr><td>{_CAP_FA.get(l['capability'], l['capability'])}</td>"
        f"<td dir='ltr'>{l['operation']}</td>"
        f"<td>{_persian_digits(str(round(l['mean_excellence'] * 100)))}٪</td>"
        f"<td>{_persian_digits(str(l['uses']))}</td></tr>"
        for l in lessons
    )
    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>داشبورد ذهن یکپارچه</title>
<meta http-equiv="refresh" content="60">
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0e1117; color: #e6e6e6; margin: 0; padding: 24px; }}
  h1 {{ font-size: 22px; color: #7aa2f7; margin: 0 0 4px; }}
  .sub {{ color: #888; font-size: 12px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 16px; }}
  .card {{ background: #161a23; border: 1px solid #23283a; border-radius: 10px; padding: 16px; }}
  .card h2 {{ font-size: 14px; color: #9ece6a; margin: 0 0 12px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }}
  .kpi {{ background: #161a23; border: 1px solid #23283a; border-radius: 10px; padding: 14px; text-align: center; }}
  .kpi .v {{ font-size: 26px; color: #7aa2f7; font-weight: 600; }}
  .kpi .l {{ font-size: 12px; color: #888; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 6px 8px; text-align: right; border-bottom: 1px solid #23283a; }}
  th {{ color: #7aa2f7; font-weight: 500; }}
  .bar {{ fill: #7aa2f7; }}
  .axis {{ stroke: #444; }}
  text {{ fill: #aaa; font-size: 10px; }}
</style>
</head>
<body>
<h1>داشبورد ذهن یکپارچه</h1>
<div class="sub">دادهی واقعی از تاریخچهی اجراها — {_persian_digits(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))} UTC</div>

<div class="kpis">
  <div class="kpi"><div class="v">{_persian_digits(str(stats.total_runs))}</div><div class="l">کل اجراها</div></div>
  <div class="kpi"><div class="v">{_persian_digits(str(round(stats.success_rate * 100)))}٪</div><div class="l">نرخ موفقیت</div></div>
  <div class="kpi"><div class="v">{_persian_digits(str(round(stats.mean_excellence * 100)))}٪</div><div class="l">میانگین داوری ARETĒ</div></div>
  <div class="kpi"><div class="v">{_persian_digits(str(len(lessons)))}</div><div class="l">درسهای planner</div></div>
</div>

<div class="grid">
  <div class="card">
    <h2>اجرا در ۱۴ روز اخیر</h2>
    <svg viewBox="0 0 320 120" width="100%">
      <line x1="10" y1="100" x2="310" y2="100" class="axis"/>
      {''.join(
          f"<rect class='bar' x='{20 + i * (290 / max(1, len(daily)))}' y='{100 - min(80, d[chr(114)+chr(117)+chr(110)+chr(115)] * 8)}' width='{max(6, 290 / max(1, len(daily)) - 6)}' height='{min(80, d[chr(114)+chr(117)+chr(110)+chr(115)] * 8)}'/>"
          for i, d in enumerate(daily)
      )}
    </svg>
  </div>
  <div class="card">
    <h2>پرکاربردترین قابلیتها</h2>
    <table><tr><th>قابلیت</th><th>اجرا</th><th>موفقیت</th></tr>{cap_rows}</table>
  </div>
  <div class="card">
    <h2>پرکاربردترین زنجیرهها</h2>
    <table><tr><th>زنجیره</th><th>اجرا</th></tr>{chain_rows}</table>
  </div>
</div>

<div class="card" style="margin-top:16px">
  <h2>⏰ زمانبندیها — چه چیزی خودش اجرا میشود</h2>
  <table><tr><th>فرمان</th><th>فاصله</th><th>وضعیت</th><th>آخرین اجرا</th></tr>{schedule_rows}</table>
  <h2 style="margin-top:14px">📁 پوشههای تحت نظر (رویداد فایل)</h2>
  <table><tr><th>پوشه</th><th>فرمان</th><th>وضعیت</th></tr>{watcher_rows}</table>
</div>

<div class="card" style="margin-top:16px">
  <h2>📈 روند داوری ARETĒ (روزانه)</h2>
  <table><tr><th>روز</th><th>میانگین داوری</th></tr>{trend_rows}</table>
</div>

<div class="card" style="margin-top:16px">
  <h2>👑 استاندارد ایستاده (تاج ARETĒ)</h2>
  <div style="font-size:15px">{crown_html}</div>
</div>

<div class="card" style="margin-top:16px">
  <h2>🎯 اهداف عامل</h2>
  <table><tr><th>هدف</th><th>گام بعدی</th><th>آخرین داوری</th><th>وضعیت</th></tr>{agent_rows}</table>
</div>

<div class="card" style="margin-top:16px">
  <h2>🧠 planner چه آموخته (از داوریهای واقعی)</h2>
  <table><tr><th>قابلیت</th><th>عملیات اثباتشده</th><th>میانگین داوری</th><th>اجراها</th></tr>{lesson_rows}</table>
</div>

</body>
</html>"""

    target = Path(out_path) if out_path else Path("artifacts") / "superplatform_dashboard.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(target), "bytes": target.stat().st_size, "error": ""}


__all__ = ["build_dashboard"]