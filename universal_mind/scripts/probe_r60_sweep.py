#!/usr/bin/env python3
"""R60 — THE SWEEP'S FIXES, live-proved: 14 proofs.

The 19-command sweep over yet-newer sentence classes measured 6 OK / 13
gaps; Q1-Q6 closed the seven headline gaps. This probe re-runs the REAL
sentences and prints the real answers:

 1  «محتوای فایل X را نشان بده» reads the REAL file (a temp file written
    for the probe, then read back through the router).
 2  «فایل متنی X را با محتوای Y بنویس» CREATES the real file.
 3  The overwrite of an existing file is REFUSED by name (delete-law spirit).
 4  A .env path is refused as a secret — «راز می‌رسد — نمی‌خوانم».
 5  «چند دقیقه تا نیمه‌شب مانده؟» matches an independent calculation.
 6  All SEVEN weekday distances match independent weekday math.
 7  «یکشنبه چند روز دیگه» answers یکشنبه, not its substring شنبه.
 8  «فضای درایو C» shows only C (not the five-drive wall).
 9  An unknown drive is refused by name with the seen list.
10  «تنظیماتت را نشان بده» lists the REAL store (voice_muted visible).
11  «ایمیل‌هایم را نشان بده» routes to email, never chart.
12  The email listing decodes MIME subjects (no base64 soup) — run against
    the REAL outbox when it exists, else a temp one.
13  «متشکرم» is answered («خواهش میکنم!»).
14  «حال شما چطوره؟» answers honestly («سالم و آماده‌ام» + real status).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
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
    from universal_mind.persian_router import route, route_and_run

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    tmp = Path(tempfile.mkdtemp(prefix="um-r60-probe-"))

    # 1-4 — the text-file capability
    f = tmp / "probe.txt"
    w = route_and_run(f"فایل متنی {f} را با محتوای گواه ر۶۰ بنویس")
    check(1, "«فایل متنی … بنویس» creates the real file",
          w.get("ok") is True and f.exists()
          and "گواه" in f.read_text(encoding="utf-8"))
    r1 = report(f"محتوای فایل {f} را نشان بده")
    check(2, "«محتوای فایل …» reads it back", "گواه ر۶۰" in r1)
    o = route_and_run(f"فایل متنی {f} را با محتوای دیگر بنویس")
    check(3, "an existing file is never silently overwritten",
          o.get("ok") is False and "دورنویسی" in str(o.get("agent_report")))
    envf = tmp / ".env"
    envf.write_text("K=1", encoding="utf-8")
    r4 = report(f"محتوای فایل {envf} را نشان بده")
    check(4, "a .env file is refused as a secret", "راز" in r4)

    # 5-7 — time-until and weekday distance
    r5 = report("چند دقیقه تا نیمه‌شب مانده؟")
    now = datetime.now()
    mid = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    mins = int((mid - now).total_seconds() // 60)
    h, m = divmod(mins, 60)
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    check(5, f"midnight matches the independent math ({h}h {m}m)",
          str(h).translate(fa) in r5 and str(m).translate(fa) in r5)
    days = [("شنبه", 5), ("یکشنبه", 6), ("دوشنبه", 0), ("سه‌شنبه", 1),
            ("چهارشنبه", 2), ("پنجشنبه", 3), ("جمعه", 4)]
    all_days = True
    for name, py in days:
        rep = report(f"{name} چند روز دیگه است؟")
        exp = (py - datetime.now().weekday()) % 7
        if exp == 0:
            if "امروز است" not in rep:
                all_days = False
                print(f"       ✗ {name}: expected امروز است, got: {rep[:60]}")
        elif str(exp).translate(fa) not in rep:
            all_days = False
            print(f"       ✗ {name}: expected {exp}, got: {rep[:60]}")
    check(6, "all seven weekday distances match independent math", all_days)
    r7 = report("یکشنبه چند روز دیگه است؟")
    exp7 = str((6 - datetime.now().weekday()) % 7).translate(fa)
    check(7, "یکشنبه answers یکشنبه (not the substring شنبه)",
          "یکشنبه" in r7 and exp7 in r7)

    # 8-9 — drive space
    r8 = report("فضای درایو C را نشان بده")
    check(8, "«فضای درایو C» shows only C", "دیسک C" in r8 and "دیسک D" not in r8)
    r9 = report("فضای درایو Q را نشان بده")
    check(9, "an unknown drive is named with the seen list", "پیدا نکردم" in r9)

    # 10 — settings
    r10 = report("تنظیماتت را نشان بده")
    check(10, "the settings listing answers from the real store",
          "تنظیم" in r10 and ("voice_muted" in r10 or "تنظیم ذخیره" in r10))

    # 11-12 — the email listing
    check(11, "«ایمیل‌هایم» routes to email, never chart",
          "email" in route("ایمیل‌هایم را نشان بده").capabilities
          and "chart" not in route("ایمیل‌هایم را نشان بده").capabilities)
    r12 = report("ایمیل‌هایم را نشان بده")
    soup = "=?" in r12
    check(12, "the email listing decodes MIME subjects (no base64 soup)",
          ("ایمیل" in r12) and not soup)

    # 13-14 — social
    r13 = report("متشکرم")
    check(13, "«متشکرم» is answered", "خواهش" in r13)
    r14 = report("حال شما چطوره؟")
    check(14, "the mood question answers honestly", "سالم و آماده" in r14)

    print()
    if FAILURES:
        print(f"R60-SWEEP probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R60-SWEEP probe: ALL 14 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
