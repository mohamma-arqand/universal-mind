"""R47 items 7-9 — THE VISIBLE DAY: today as one live Persian HTML page.

The probe of R46 proved the platform can LIVE a full day; this module makes
the day SEEABLE. One RTL page, written next to the store, rebuilt whenever
asked («صفحهی امروز را بساز») or on every tick — everything on it is real
data from today: the morning briefing, every run (route + verdict + shield),
the reminders that fire, the named memories, the tick pulse, the live
verdicts. Persian digits, minimal cards, no decoration that lies.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_FA = str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")


def _fa(value: Any) -> str:
    return str(value).translate(_FA)


def _today() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d")


def _esc(text: str) -> str:
    return (text.replace("&", "&").replace("<", "<")
            .replace(">", ">"))


def _today_runs(db: DatabaseSuite) -> list[dict[str, Any]]:
    q = db.query(
        "SELECT command, route, succeeded, excellence, verified, "
        "created_at FROM run_history "
        "WHERE date(created_at) = date(datetime('now', 'localtime')) "
        "ORDER BY id DESC LIMIT 60"
    )
    return q.get("rows", []) if q.get("ok") else []


def _today_judgments(db: DatabaseSuite) -> list[dict[str, Any]]:
    try:
        from universal_mind.live_judge import latest_live_judgments

        return latest_live_judgments(limit=8, db=db)
    except Exception:  # noqa: BLE001 — a page never dies on one card
        return []


def _today_reminders(db: DatabaseSuite) -> list[dict[str, Any]]:
    q = db.query(
        "SELECT message, fire_at FROM reminders "
        "WHERE date(fire_at) = date(datetime('now', 'localtime')) "
        "ORDER BY fire_at LIMIT 12"
    )
    return q.get("rows", []) if q.get("ok") else []


def _today_memories(db: DatabaseSuite) -> list[dict[str, Any]]:
    try:
        from universal_mind.named_memory import recall_facts

        return recall_facts(limit=5, db=db)
    except Exception:  # noqa: BLE001
        return []


def _tick_pulse(db: DatabaseSuite) -> dict[str, Any]:
    q = db.query(
        "SELECT state, fired, skipped, created_at FROM tick_health "
        "ORDER BY id DESC LIMIT 1"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return rows[0] if rows else {}


def _briefing(db: DatabaseSuite) -> str:
    try:
        from universal_mind.daily_briefing import today_briefing

        return today_briefing(db=db)
    except Exception:  # noqa: BLE001
        return ""


def build_today_page(db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Render today as one HTML page. Returns path + counts (auditable)."""
    store = db or DatabaseSuite.shared_persistent()
    runs = _today_runs(store)
    judgments = _today_judgments(store)
    reminders = _today_reminders(store)
    memories = _today_memories(store)
    pulse = _tick_pulse(store)
    briefing = _briefing(store)

    wins = sum(1 for r in runs if int(r.get("succeeded") or 0) == 1)
    shield = sum(1 for r in runs if int(r.get("verified") or 0) == 1)

    rows_html = "".join(
        f"<tr><td>{_esc(str(r['command'])[:80])}</td>"
        f"<td><code>{_esc(str(r['route']))}</code></td>"
        f"<td class=\"{'ok' if int(r.get('succeeded') or 0) else 'bad'}\">"
        f"{'✅' if int(r.get('succeeded') or 0) else '❌'}</td>"
        f"<td>{'🛡' if int(r.get('verified') or 0) else '—'}</td></tr>"
        for r in runs
    ) or "<tr><td colspan=\"4\">امروز هنوز فرمانی اجرا نشده</td></tr>"

    judge_html = "".join(
        "<li>" + _esc(j["reason"][:90]) + " "
        + '<span class="score">(' + _fa(f"{j['llm']:.2f}") + ")"
        + "</span></li>"
        for j in judgments
    ) or "<li>داورِ زنده هنوز امروز قضاوت نکرده</li>"

    remind_html = "".join(
        f"<li>⏰ {_esc(str(r['message'])[:70])} — {_esc(str(r['fire_at'])[:16])}</li>"
        for r in reminders
    ) or "<li>یادآورِ امروزِ خاصی نیست</li>"

    memory_html = "".join(
        f"<li>📌 {_esc(str(m)[:90])}</li>" for m in memories
    ) or "<li>حافظهی نامیِ فعالی نیست</li>"

    pulse_state = str(pulse.get("state") or "—")
    pulse_color = "ok" if pulse_state == "ok" else "bad"
    pulse_time = _esc(str(pulse.get("created_at") or "—")[:16])

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>امروز — {_today()}</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: "Vazirmatn", Tahoma, sans-serif; background: #0e1116;
         color: #d8dee9; margin: 0; padding: 24px; }}
  h1 {{ font-size: 1.35rem; margin: 0 0 4px; }}
  h2 {{ font-size: .95rem; color: #7aa2f7; margin: 20px 0 8px; }}
  .sub {{ color: #5c6370; font-size: .8rem; margin-bottom: 18px; }}
  .cards {{ display: grid; grid-template-columns: repeat(4, 1fr);
           gap: 10px; margin-bottom: 8px; }}
  .card {{ background: #161b22; border: 1px solid #21262d;
          border-radius: 10px; padding: 12px 14px; }}
  .card .n {{ font-size: 1.5rem; font-weight: 700; }}
  .card .l {{ color: #5c6370; font-size: .75rem; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22;
          border-radius: 10px; overflow: hidden; font-size: .8rem; }}
  th, td {{ padding: 7px 10px; text-align: right;
           border-bottom: 1px solid #21262d; }}
  th {{ background: #1c2129; color: #7aa2f7; font-weight: 600; }}
  td.ok {{ color: #9ece6a; }} td.bad {{ color: #f7768e; }}
  ul {{ margin: 0; padding: 0 18px 0 0; font-size: .82rem; line-height: 1.9; }}
  .score {{ color: #7aa2f7; }}
  .pulse {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
           font-size: .75rem; }}
  .pulse.ok {{ background: #1a2b1e; color: #9ece6a; }}
  .pulse.bad {{ background: #2b1a1e; color: #f7768e; }}
  .brief {{ background: #161b22; border-right: 3px solid #7aa2f7;
           border-radius: 8px; padding: 10px 14px; font-size: .82rem;
           white-space: pre-wrap; }}
  code {{ background: #1c2129; padding: 1px 6px; border-radius: 5px;
         font-size: .75rem; }}
</style>
</head>
<body>
<h1>☀️ امروز — {_fa(_today())}</h1>
<div class="sub">صفحهی زندهی امروز؛ همهچیز از دادهی واقعی امروز</div>
<div class="cards">
  <div class="card"><div class="n">{_fa(len(runs))}</div><div class="l">فرمان امروز</div></div>
  <div class="card"><div class="n">{_fa(wins)}</div><div class="l">موفق</div></div>
  <div class="card"><div class="n">{_fa(shield)}</div><div class="l">تأییدِ فایل 🛡</div></div>
  <div class="card"><div class="n"><span class="pulse {pulse_color}">{_esc(pulse_state)}</span></div><div class="l">آخرین تپش — {pulse_time}</div></div>
</div>
<h2>بریفینگ صبحگاهی</h2>
<div class="brief">{_esc(briefing) or "بریفینگ امروز نوشته نشده"}</div>
<h2>فرمانهای امروز</h2>
<table>
<tr><th>فرمان</th><th>مسیر</th><th>نتیجه</th><th>تأیید</th></tr>
{rows_html}
</table>
<h2>⚖ داورِ زنده (نمونههای امروز)</h2>
<ul>{judge_html}</ul>
<h2>⏰ یادآورهای امروز</h2>
<ul>{remind_html}</ul>
<h2>📌 حافظهی نامی</h2>
<ul>{memory_html}</ul>
</body>
</html>"""

    out = Path(store.db_path).parent / "today.html"
    out.write_text(html, encoding="utf-8")
    return {"ok": True, "path": str(out),
            "runs": len(runs), "wins": wins, "shield": shield,
            "judgments": len(judgments), "reminders": len(reminders),
            "memories": len(memories)}


__all__ = ["build_today_page"]
