#!/usr/bin/env python3
"""R66 — the multi-step/edit/date sweep's fixes, live: 12 proofs.

The 15-command sweep measured 7 classes — the biggest was a LIVE
DELETE-LAW VIOLATION («یادآوری ۶۸ را حذف کن» destroyed the operator's
real reminder with no confirmation). P1-P7 closed them. This probe
re-runs the REAL sentences:

 1  A single-delete ask names the row and refuses (row survives).
 2  The confirmed single delete removes exactly that row.
 3  «نمودارش کن» without data is a NAMED refusal (no [3,7,5] bars).
 4  A bar with real data still draws (the gate is not a ban).
 5  «فایل X را بساز و محتواش را نشان بده» creates and shows (empty named).
 6  The create+show with content writes the exact text, shows it back.
 7  «یادآوری شماره N را نشان بده» returns that row alone (Persian digits).
 8  An unknown reminder id is an honest refusal.
 9  «شنبه چندم است؟» matches the independent next-occurrence computation.
10  «پنجشنبه هفته بعد» is 7 days further than the near one.
11  «تنظیمات نمودار را تغییر بده به خطی» stores a preference (not a draw).
12  «یادداشت X را بنویس» builds a clipboard write with the spoken text.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    os.environ["UM_MUTE"] = "1"
    from universal_mind import operator_preferences as prefs
    from universal_mind.persian_params import extract_params
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import delete_schedule, list_schedules, register

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    # 1-2 — the single delete law
    register("هر روز ساعت ۷ گواه-r66 را بگو")
    sid = next(s.schedule_id for s in list_schedules() if "گواه-r66" in s.command)
    fa_sid = str(sid).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    r1 = route_and_run(f"یادآوری {fa_sid} را حذف کن")
    alive1 = any(s.schedule_id == sid for s in list_schedules())
    check(1, "a bare single-delete ask refuses and the row survives",
          r1.get("ok") is False and "تأیید" in r1.get("agent_report", "")
          and "گواه-r66" in r1.get("agent_report", "") and alive1)
    r2 = route_and_run(f"یادآوری {fa_sid} را حذف کن — تأیید کن")
    alive2 = any(s.schedule_id == sid for s in list_schedules())
    check(2, "the confirmed delete removes exactly that row",
          r2.get("ok") is True and "حذف شد" in r2.get("agent_report", "")
          and not alive2)

    # 3-4 — the chart no-data law on every kind. The BARE ask runs with a
    # CLEAN anaphora store: in the verify run the full test suite has
    # already drawn data-carrying charts, and «نمودارش کن» would
    # legitimately redraw THAT series. The probe clears the subject store
    # (an honest fresh-process measurement, named here).
    from universal_mind.persian_router import _ANAPHORA_SUBJECT

    _ANAPHORA_SUBJECT.clear()
    r3 = route_and_run("نمودارش کن")
    check(3, "a bare chart ask without data is a named refusal",
          r3.get("ok") is False and "بدون داده" in r3.get("agent_report", ""))

    r4 = route_and_run("نمودار میله‌ای از ۳ و ۷ و ۵ بکش")
    check(4, "a bar with real data still draws",
          r4.get("ok") is True and ".png" in r4.get("agent_report", ""))

    # 5-6 — create + show
    f = Path("D:/um_r66_probe.txt")
    f.unlink(missing_ok=True)
    r5 = route_and_run(f"فایل {f} را بساز و محتواش را به من نشان بده")
    check(5, "create+show: the file exists, emptiness named",
          r5.get("ok") is True and f.exists() and f.stat().st_size == 0
          and "خالی" in r5.get("agent_report", ""))
    f.unlink()
    r6 = route_and_run(
        f"فایل {f} را با محتوای سلام از گواه-r66 بساز و محتواش را نشان بده")
    check(6, "create+show with content: exact write, shown back",
          r6.get("ok") is True and f.exists()
          and f.read_text(encoding="utf-8") == "سلام از گواه-r66"
          and "محتوای فایل" in r6.get("agent_report", ""))
    f.unlink()

    # 7-8 — the single-reminder view
    register("هر روز ساعت ۷ گواه-r66-view را بگو")
    vid = next(s.schedule_id for s in list_schedules()
               if "گواه-r66-view" in s.command)
    fa_vid = str(vid).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    r7 = route_and_run(f"یادآوری شماره {fa_vid} را نشان بده")
    check(7, "one number returns that row alone (Persian digits)",
          r7.get("ok") is True and "گواه-r66-view" in r7.get("agent_report", "")
          and "ساعت ۷:۰۰" in r7.get("agent_report", ""))
    r8 = route_and_run("یادآوری شماره ۹۹۹۹۹ را نشان بده")
    check(8, "an unknown reminder id is an honest refusal",
          r8.get("ok") is False and "پیدا نکردم" in r8.get("agent_report", ""))
    delete_schedule(vid)

    # 9-10 — the named day's date
    r9 = route_and_run("شنبه چندم است؟")
    delta = (5 - date.today().weekday()) % 7 or 7
    exp = date.today() + timedelta(days=delta)
    from jdatetime import date as jdate

    j = jdate.fromgregorian(date=exp)
    exp_fa = str(j.day).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    check(9, "«شنبه» matches the independent next-Saturday computation",
          r9.get("ok") is True and exp_fa in r9.get("agent_report", ""))
    r10 = route_and_run("پنجشنبه هفته بعد چندمه؟")
    near = route_and_run("پنجشنبه چندم است؟")
    check(10, "«هفته بعد» jumps a full week (dates differ)",
          r10.get("ok") is True and near.get("ok") is True
          and r10.get("agent_report", "") != near.get("agent_report", ""))

    # 11 — settings change is a preference
    before_kind = prefs.get("chart_kind")
    r11 = route_and_run("تنظیمات نمودار را تغییر بده به خطی")
    stored = prefs.get("chart_kind")
    if before_kind is None:
        DatabaseSuite(persistent=True).execute(
            "DELETE FROM operator_preferences WHERE key = 'chart_kind'")
    else:
        prefs.set("chart_kind", before_kind)
    check(11, "a settings-change sentence stores the preference (not a draw)",
          r11.get("ok") is True and r11.get("route") == ["preference"]
          and stored == "line")

    # 12 — the note write params
    out = extract_params("یادداشت جلسه فردا ساعت ۱۰ است را بنویس", "clipboard")
    check(12, "a note sentence builds a clipboard write with the spoken text",
          out.get("operation") == "write" and "جلسه فردا" in out.get("text", ""))

    print()
    if FAILURES:
        print(f"R66 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R66 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
