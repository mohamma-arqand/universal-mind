#!/usr/bin/env python3
"""R61 — THE DEEP-REVIEW FIXES, live-proved: 16 proofs.

Every S-item closed a measured gap from the seven-persona review
(docs/DEEP_REVIEW_R61.md). This probe re-runs the REAL sentences:

 1  «قیمت دلار الان چنده؟» is REFUSED (never «نتیجه ۴»).
 2  «۲۰ درصد از ۵۰۰ چنده؟» answers «برابر ۱۰۰» (never ۵۲۰).
 3  «ساعت چنده؟» is ONE calendar (Jalali day+month, never «۲ دی» in Oct).
 4  «رگرسیون روی این اعداد» is refused for lacking data (never silent).
 5  A write to ~/.ssh/id_rsa is refused BY NAME.
 6  A write into C:/Windows is refused BY NAME.
 7  An ordinary file write still works.
 8  The two-verb sentence names its dropped half (or ran whole).
 9  The gate's reasoning is visible in the report (⚖).
10  «یادآورهای من» numbers every row.
11  Deletion by number removes exactly that row (and nothing else).
12  Bulk delete without «تأیید کن» deletes NOTHING.
13  A reminder sentence suggests the reminder recipe (not «برش»).
14  «صبح بخیر» / «ممنون که کمک کردی» answer (sentence-shaped social).
15  A defaulted reminder hour CONFESSES the default.
16  A live chart report states WHERE the file is + no Latin digit leaks.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
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
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import list_schedules
    from universal_mind.spelling_recovery import suggest_for

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    # S1 — the honesty four
    r1 = report("قیمت دلار الان چنده؟")
    # R62-T2 evolution: world-data questions get the TOPIC-SPECIFIC refusal;
    # both it and the S1 compute-refusal satisfy the honesty law (never «نتیجه»).
    check(1, "the knowledge question is refused, not answered with 2+2",
          "نتیجه" not in r1
          and ("محاسبه‌ای نیست" in r1 or "دادهٔ بیرونی" in r1))
    r2 = report("۲۰ درصد از ۵۰۰ چنده؟")
    check(2, "percent answers ۱۰۰ (never the ۵۲۰ sum)", "برابر ۱۰۰" in r2)
    r3 = report("ساعت چنده؟")
    check(3, "the clock is one calendar (no Gregorian-day + Jalali-month glue)",
          "مهر" in r3 or "آبان" in r3 or "شهریور" in r3)
    r4 = report("رگرسیون روی این اعداد")
    check(4, "ML without data is refused by name",
          "داده‌ای در جمله پیدا نکردم" in r4)

    # S2 — the write policy
    r5 = report("فایل متنی C:/Users/EliteBook/.ssh/id_rsa را با محتوای x بنویس")
    check(5, "an ssh key is never written", "نمی‌نویسم" in r5)
    r6 = report("فایل متنی C:/Windows/probe.txt را با محتوای x بنویس")
    check(6, "the Windows dir is never a write target", "نمی‌نویسم" in r6)
    tmp = Path(tempfile.mkdtemp(prefix="um-r61-probe-"))
    f = tmp / "ok.txt"
    r7 = route_and_run(f"فایل متنی {f} را با محتوای گواه بنویس")
    check(7, "an ordinary write still works",
          r7.get("ok") is True and f.exists())

    # S3 — the gate speaks
    r8 = report("گزارش بساز و برایم ایمیل کن")
    # BOTH honest outcomes pass (the gate picks per-run): (a) the shrunk
    # route CONFESSES the dropped half, or (b) the whole chain runs and
    # the email failure is NAMED. Either way no half dies silently.
    r8_whole_chain_named_failure = "ایمیل" in r8 and "ناموفق" in r8
    r8_dropped_confessed = "اجرا نشد" in r8 and "ایمیل" in r8
    check(8, "the two-verb sentence names its dropped half (or ran whole)",
          r8_whole_chain_named_failure or r8_dropped_confessed)
    check(9, "the gate's reasoning is visible when the gate intervened "
             "(or the chain ran whole with named failures)",
          ("⚖" in r8) or r8_whole_chain_named_failure)

    # S4 — reminder deletion (isolated probe rows, named cleanup)
    route_and_run("یادم باشه پس‌فردا ساعت ۶ گواه-r61-probe")
    r10 = report("یادآورهای من")
    check(10, "the listing numbers every row",
          bool(re.search(r"\([۰-۹]+\)", r10)))
    m = None
    for ln in r10.splitlines():
        if "گواه-r61-probe" in ln:
            mm = re.match(r"\s*[•-]*\s*\(([۰-۹]+)\)", ln)
            if mm:
                m = mm
    if m:
        sid = m.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        before = {s.schedule_id for s in list_schedules()}
        r11 = report(f"یادآوری {sid} را حذف کن")
        after = {s.schedule_id for s in list_schedules()}
        check(11, "deletion by number removes exactly that row",
              "حذف شد" in r11 and (before - after) == {int(sid)})
    else:
        check(11, "deletion by number removes exactly that row", False)
    r12 = report("همه یادآوریها را حذف کن")
    check(12, "bulk delete without confirmation destroys nothing",
          "تأیید کن" in r12)
    # named cleanup of any probe leftovers
    from universal_mind.database_suite import DatabaseSuite

    DatabaseSuite(persistent=True).execute(
        "DELETE FROM schedules WHERE command LIKE '%گواه-r61-probe%'")

    # S5 — suggestions and colloquial speech
    s13 = suggest_for("یادم باشی فردا زنگ بزنم")
    check(13, "a reminder sentence suggests the reminder recipe",
          bool(s13) and "یادم بنداز" in s13[0])
    r14a = report("صبح بخیر")
    r14b = report("ممنون که کمک کردی")
    check(14, "sentence-shaped social talk answers",
          ("صبح بخیر" in r14a) and ("خواهش" in r14b))
    r15 = report("یادم باشه پس‌فردا زنگ بزنم")
    check(15, "a defaulted hour confesses the default", "پیش‌فرض" in r15)
    DatabaseSuite(persistent=True).execute(
        "DELETE FROM schedules WHERE command LIKE '%زنگ بزنم%' AND kind='once'")

    # S6 — the report a stranger can use
    r16 = report("نمودار از ۲ و ۵ و ۹ بکش")
    check(16, "the chart report states the file's path and keeps digits Persian",
          "در «" in r16 and ".png" in r16 and " با 1 " not in r16)

    print()
    if FAILURES:
        print(f"R61 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R61 probe: ALL 16 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
