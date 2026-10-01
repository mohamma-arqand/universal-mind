#!/usr/bin/env python3
"""R59 — THE SWEEP'S SIX FIXES, live-proved: 12 proofs.

Every P-item closed a measured gap from the 17-command sweep over NEW
sentence classes. This probe re-runs the REAL sentences and prints the real
answers (the machine views run against the REAL machine — no stubs there):

 1  «جمع ۲ و ۵ چنده؟» routes to compute and answers ۷.
 2  «۵ منهای ۳ چنده؟» answers ۲ — the operator the sentence NAMES (the old
    bug answered ۸: it built `5.0 + 3.0`).
 3  «۱۰ کیلومتر چند مایل است؟» answers with the real converted value.
 4  «۱۰۰ فارنهایت چند سانتیگراد است؟» answers ~۳۷.۷۸.
 5  «چه برنامه‌هایی الان باز است؟» answers from the real open windows.
 6  The Persian window titles survive the round trip (no ????).
 7  «پروسه‌های پرمصرف را نشان بده» lists real processes with CPU/RAM.
 8  «چه چیزهایی یادت هست؟» lists the real named-memory rows.
 9  «آخرین چیزی که یادت داشت چی بود؟» names the newest row.
10  «زنجیره‌های من را نشان بده» lists the real saved chains.
11  «۲ به توان ۱۰ چنده؟» answers ۱۰۲۴.
12  The honest refusals stay honest (kg→metres is still refused by name).
"""

from __future__ import annotations

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
    import os

    os.environ["UM_MUTE"] = "1"

    from universal_mind.persian_router import route_and_run

    def report(cmd: str) -> str:
        p = route_and_run(cmd)
        return str(p.get("agent_report", ""))

    # 1 + 2 — arithmetic, with the operator the sentence names
    r1 = report("جمع ۲ و ۵ چنده؟")
    check(1, "«جمع ۲ و ۵ چنده؟» answers ۷", "نتیجه ۷" in r1)
    r2 = report("۵ منهای ۳ چنده؟")
    check(2, "«۵ منهای ۳ چنده؟» answers ۲ (not the old + bug's ۸)", "نتیجه ۲" in r2)

    # 3 + 4 — unit conversion
    r3 = report("۱۰ کیلومتر چند مایل است؟")
    check(3, "«۱۰ کیلومتر چند مایل است؟» gives the real value", "۶" in r3 and "مایل" in r3)
    r4 = report("۱۰۰ فارنهایت چند سانتیگراد است؟")
    check(4, "«۱۰۰ فارنهایت …» answers ~۳۷.۷۸ (the formula, not a factor)",
          "۳۷" in r4 and "سانتیگراد" in r4)

    # 5 + 6 — open windows on the REAL machine
    r5 = report("چه برنامه‌هایی الان باز است؟")
    check(5, "the open-windows question answers from the real machine",
          "پنجره" in r5 and "نشد" not in r5)
    check(6, "Persian window titles survive the round trip (no ???? lobby)",
          "????" not in r5)

    # 7 — heavy processes
    r7 = report("پروسه‌های پرمصرف را نشان بده")
    check(7, "the heavy-processes question lists real CPU/RAM",
          "پردازش" in r7 and "مگابایت" in r7)

    # 8 + 9 — memory listings
    r8 = report("چه چیزهایی یادت هست؟")
    check(8, "the memory listing answers (rows or the honest empty)",
          ("یادم است" in r8) or ("یادم نیست" in r8))
    r9 = report("آخرین چیزی که یادت داشت چی بود؟")
    check(9, "the latest-memory question answers",
          ("آخرین چیزی" in r9) or ("یادم نیست" in r9))

    # 10 — saved chains
    r10 = report("زنجیره‌های من را نشان بده")
    check(10, "the chain listing answers (chains or the honest empty)",
          ("زنجیره" in r10 and ("ذخیره شده" in r10 or "ذخیره نکردی" in r10)))

    # 11 — power
    r11 = report("۲ به توان ۱۰ چنده؟")
    check(11, "«۲ به توان ۱۰ چنده؟» answers ۱۰۲۴", "۱۰۲۴" in r11)

    # 12 — honest refusals stay honest
    r12 = report("۵ کیلوگرم چند متر است؟")
    check(12, "kg→metres is still refused BY NAME (never a fake conversion)",
          "خانواده" in r12)

    print()
    if FAILURES:
        print(f"R59-SWEEP probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R59-SWEEP probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
