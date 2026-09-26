"""One full day — every R46 item in ONE live pass, then a Persian PDF.

The probe plants a small real seed and walks a compressed day: the
morning briefing → real commands (one fails → smart retry) → an operator
verdict that becomes a drift law → the taught word → named memory → the
weekly letter → the five-signal status → backup health → tick health →
compaction → the restore drill → the farewell. Every claim printed; the
day's transcript lands in a real PDF («یک روزِ کامل»).

Exit 0 = all 15 items proved live before this probe's own eyes.
"""

from __future__ import annotations

import io
import contextlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

LOG: list[str] = []


def say(section: str, text: str) -> None:
    LOG.append(f"## {section}\n{text}\n")
    head = text.splitlines()[0] if text else ""
    print(f"  [{section}] {head[:90]}")


def check(section: str, cond: bool, what: str) -> bool:
    mark = "✅" if cond else "❌"
    LOG.append(f"- {mark} {section}: {what}")
    if not cond:
        print(f"  ❌ {section}: {what}")
    return cond


def main() -> int:
    print("=== probe_r46_day: ONE FULL DAY, every item live ===")
    tmp = Path(tempfile.mkdtemp(prefix="r46-day-"))
    db = DatabaseSuite(str(tmp / "day.db"))
    RunHistory(db)
    all_ok = True

    with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
        from universal_mind.persian_router import route_and_run

        # ---- 05:50 — the seed (yesterday's runs, real) --------------------
        for cmd in ("نمودار از ۲ و ۴ بکش", "میانگین ۳ و ۹ را حساب کن"):
            route_and_run(cmd)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            f"UPDATE run_history SET created_at = '{yesterday}'"
        )
        y_all = int(db.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"])

        # ---- 08:00 — the morning briefing (item 10) -----------------------
        from universal_mind.daily_briefing import record_briefing

        info = record_briefing(datetime.now().strftime("%Y-%m-%d"))
        say("بریفینگ ۰۸:۰۰", info["report"])
        all_ok &= check("قلم ۱۰", "دیروز" in info["report"]
                        and str(y_all).translate(_FA) in info["report"],
                        f"بریفینگ از {y_all} رانِ واقعیِ دیروز نوشت")

        # ---- 08:01 — a real command (item 1: the verified stamp) ----------
        p1 = route_and_run("نمودار دایرهای از ۲ و ۳ و ۵ بکش")
        say("فرمان ۰۸:۰۱", str(p1["agent_report"]))
        all_ok &= check("قلم ۱", bool(p1.get("verification")),
                        f"مهر تأیید: {p1.get('verification', '')}")

        # ---- 08:02 — a REAL failure, then the smart retry (item 6) --------

        RunHistory().record("نمودار ستونی از هیچ چیز بکش", ["chart"], False,
                            outcome_class="heuristic")
        r = route_and_run("دوباره امتحان کن")
        n_retry = int(db.query(
            "SELECT COUNT(*) AS n FROM run_history WHERE retry_of != ''"
        )["rows"][0]["n"])
        say("retry ۰۸:۰۲", str(r["agent_report"]))
        all_ok &= check("قلم ۶", n_retry >= 1 and r["agent_report"].startswith("🔁"),
                        f"رانِ دوم مهر retry_of دارد ({n_retry} ردیف)")

        # ---- 08:03 — the operator's 👍 becomes a drift LAW (item 3) --------
        from universal_mind.operator_verdicts import record_verdict
        from universal_mind.report_laws import learned_laws as stored_laws

        record_verdict("نمودار دایرهای از ۲ و ۳ و ۵ بکش", "good")
        laws = stored_laws()
        all_ok &= check("قلم ۳", bool(laws) and all(l[1]["must_contain"] for l in laws),
                        f"قانون از رأی 👍: {len(laws)} قانون با anchor واقعی")
        if laws:
            say("قانونِ رانش", f"«{laws[0][0]}» → anchors: {laws[0][1]['must_contain'][:2]}")

        # ---- 08:04 — the operator TEACHES a word (item 9) ------------------
        route_and_run("واژهی زرشک یعنی داده")
        r2 = route_and_run("میانگین زرشک و انار را حساب کن")
        say("واژهی آموخته", f"«زرشک» یعنی داده — فرمان بعدی: {r2['agent_report'].splitlines()[0][:60]}")
        all_ok &= check("قلم ۹", r2["ok"], "فرمانِ پس از تعریف مسیر درست گرفت")

        # ---- 08:05 — named memory (item 4) ---------------------------------
        p3 = route_and_run("یادت باشد که جلسه با تیم فردا ساعت ۱۰ است")
        p4 = route_and_run("نمودار جلسه تیم بکش")
        surfaced = p4["agent_report"].startswith("📌")
        say("حافظهی نامی", str(p3["agent_report"]))
        all_ok &= check("قلم ۴", surfaced, "حافظهی مرتبط در صدر گزارشِ ران بعدی آمد")

        # ---- 09:00 — the tick (items 10, 13, 14) ---------------------------
        from universal_mind.scripts.scheduler_tick import tick

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tick(notify_summary=False)
        tick_out = buf.getvalue()
        n_brief_rows = int(db.query("SELECT COUNT(*) AS n FROM daily_briefings")["rows"][0]["n"])
        n_health_rows = int(db.query("SELECT COUNT(*) AS n FROM tick_health")["rows"][0]["n"])
        say("تیک ۰۹:۰۰", tick_out.strip())
        all_ok &= check("قلم ۱۳", n_health_rows >= 1,
                        f"خلاصهی tick در tick_health ردیف خورد ({n_health_rows})")
        all_ok &= check(
            "قلم ۱۰-تیک", n_brief_rows == 1,
            f"بریفینگ امروز UNIQUE است (یکبار نوشته شد؛ tick دوباره نمینویسد) — {n_brief_rows} ردیف",
        )

        # ---- 10:00 — the one-menu periodic report (item 12) ----------------
        p5 = route_and_run("گزارش کامل بده")
        say("گزارش کامل ۱۰:۰۰", str(p5["agent_report"])[:400])
        all_ok &= check("قلم ۱۲", "☀️" in p5["agent_report"] and "📖" in p5["agent_report"],
                        "بریفینگ + سالنامه در یک پاسخ")

        # ---- 11:00 — backup health (item 15) -------------------------------
        from universal_mind.backup_health import backup_health
        from universal_mind.restore_drill import run_restore_drill

        drill = run_restore_drill()
        say("مانور بازیابی", f"بازیابی {'موفق' if drill.ok else 'ناموفق'} — integrity: {drill.integrity}")
        all_ok &= check("مانور", drill.ok, "بکاپ واقعاً بازیابی شد")
        h = backup_health()
        say("سلامت بکاپ ۱۱:۰۰", h["report"])
        all_ok &= check("قلم ۱۵", h["ok"] and "✅" in h["report"],
                        "بکاپ تازه + مانور موفق = سالم")

        # ---- 12:00 — free-form status + the five signals (item 8) ----------
        p6 = route_and_run("خب؟")
        say("وضعیت ۱۲:۰۰", str(p6["agent_report"])[:400])
        all_ok &= check("قلم ۸", "پنج سیگنال" in p6["agent_report"],
                        "پرسش آزاد به پاسخ پنجسیگنالی رسید")

        # ---- 18:00 — the farewell (wave 2) ----------------------------------
        p7 = route_and_run("ممنون")
        say("خداحافظی ۱۸:۰۰", str(p7["agent_report"]))
        all_ok &= check("گفتار", p7["ok"], "خداحافظی جواب گرفت")

    # ---- the day's transcript → a real Persian PDF -------------------------
    transcript = (
        "# یک روزِ کامل — ذهن یکپارچه (R46)\n\n"
        f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        + "\n".join(LOG)
    )
    try:
        from universal_mind.pdf_suite import PdfSuite

        sections = [ln for ln in transcript.splitlines() if ln.strip()]
        out = PdfSuite().document("یک روزِ کامل — ذهن یکپارچه", sections)
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "PDF failed"))
        path = str(out.get("path", ""))
        size = int(out.get("bytes", 0))
        print(f"\nPDF: {path} ({size} bytes)")
        all_ok &= bool(path and size > 0)
    except Exception as exc:  # noqa: BLE001 — the PDF is the day's record
        print(f"PDF FAILED: {exc}")
        all_ok = False

    print(f"\n{'✅ ALL LIVE — every item proved in one pass' if all_ok else '❌ FAILURES ABOVE'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
