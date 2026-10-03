#!/usr/bin/env python3
"""R70 — the conversions/text/appointments sweep's fixes, live: 12 proofs.

 1  «۵ کیلوگرم چند پوند است؟» runs unitconvert ALONE (no vitals chain).
 2  «۱۰۰ فارنهایت» answers 37.8C in Persian digits.
 3  «در فایل X چند کلمه هست؟» counts the real words/lines.
 4  A missing word-count file is an honest refusal.
 5  «فردا چند تا قرار دارم؟» counts TOMORROW'S rows, each named.
 6  «پس‌فردا» is its own day (the substring law — no farda rows leak).
 7  «برنامه این هفته‌ام» lists the week's real rows.
 8  A DONE goal never appears under «کارهای ناتمام».
 9  «بین ۱۰ و ۲۰ چند عدد اول؟» answers the real primes (11,13,17,19).
10  A prime-free range says so plainly.
11  «۳۰ دقیقه دیگر هشدار بده» registers (relative delta regression).
12  The blanket reminder count still answers (regression).
"""

from __future__ import annotations

import os
import sys
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
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import (
        delete_schedule,
        list_schedules,
        register_one_shot,
    )

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r70p%'")

    # 1-2 — the conversion ownership
    p1 = route_and_run("۵ کیلوگرم چند پوند است؟")
    check(1, "a conversion runs unitconvert alone",
          p1.get("route") == ["unitconvert"])
    p2 = route_and_run("۱۰۰ درجه فارنهایت چند سانتیگراد است؟")
    check(2, "100F answers 37.8C in Persian digits",
          p2.get("ok") is True and "۳۷" in str(p2.get("agent_report", "")))

    # 3-4 — the word count
    f = Path("D:/um_r70_probe.txt")
    f.write_text("سلام دنیا این یک فایل گواه است", encoding="utf-8")
    p3 = route_and_run(f"در فایل {f} چند کلمه هست؟")
    check(3, "the real word/line count",
          p3.get("ok") is True and "۷ کلمه" in str(p3.get("agent_report", ""))
          and "۱ سطر" in str(p3.get("agent_report", "")))
    p4 = route_and_run("در فایل D:/um_r70_missing_zz.txt چند کلمه هست؟")
    check(4, "a missing file is an honest refusal",
          p4.get("ok") is False and "پیدا نکردم" in str(p4.get("agent_report", "")))
    f.unlink(missing_ok=True)

    # 5-6 — the day-scoped appointments
    register_one_shot("فردا ساعت ۱۰ جلسه گواه-r70p")
    p5 = route_and_run("فردا چند تا قرار دارم؟")
    rep5 = str(p5.get("agent_report", ""))
    check(5, "tomorrow's count with the row named",
          p5.get("ok") is True and "فردا ۱ قرار" in rep5
          and "جلسه گواه-r70p" in rep5)
    p6 = route_and_run("پس‌فردا چند تا قرار دارم؟")
    rep6 = str(p6.get("agent_report", ""))
    check(6, "«پس‌فردا» is its own day (substring law)",
          p6.get("ok") is True and "هیچ قرار" in rep6
          and "جلسه" not in rep6)

    # 7 — the week's plan
    p7 = route_and_run("برنامه این هفته‌ام را نشان بده")
    check(7, "the week lists the real rows",
          p7.get("ok") is True
          and "برنامهٔ این هفته" in str(p7.get("agent_report", ""))
          and "جلسه گواه-r70p" in str(p7.get("agent_report", "")))

    # 8 — the unfinished list never shows done goals
    p8 = route_and_run("چه کارهای ناتمامی دارم؟")
    rep8 = str(p8.get("agent_report", ""))
    check(8, "a done goal never appears under unfinished",
          p8.get("ok") is True and "— done" not in rep8)

    # 9-10 — the primes
    p9 = route_and_run("بین ۱۰ و ۲۰ چند عدد اول هست؟")
    check(9, "the real primes in the range",
          p9.get("ok") is True and p9.get("route") == ["data"]
          and "۴ عدد اول" in str(p9.get("agent_report", ""))
          and "۱۱، ۱۳، ۱۷، ۱۹" in str(p9.get("agent_report", "")))
    p10 = route_and_run("بین ۲۴ و ۲۸ چند عدد اول هست؟")
    check(10, "a prime-free range says so",
          p10.get("ok") is True
          and "هیچ عدد اولی" in str(p10.get("agent_report", "")))

    # 11-12 — the regressions
    p11 = route_and_run("۳۰ دقیقه دیگر هشدار بده-r70p")
    row11 = next((s for s in list_schedules()
                  if "هشدار بده-r70p" in s.command), None)
    check(11, "the relative delta still registers (30 min)",
          p11.get("ok") is True and row11 is not None)
    p12 = route_and_run("چند تا یادآور داری؟")
    check(12, "the blanket reminder count still answers",
          p12.get("ok") is True
          and "یادآور" in str(p12.get("agent_report", "")))

    # cleanup
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r70p%'")
    for s in list_schedules():
        if "گواه-r70p" in s.command or "هشدار بده-r70p" in s.command:
            delete_schedule(s.schedule_id)

    print()
    if FAILURES:
        print(f"R70 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R70 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
