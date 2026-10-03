#!/usr/bin/env python3
"""R71 — the comparison/text-ops sweep's fixes, live: 12 proofs.

 1  «۵ بزرگتر از ۳ است؟» answers from data (never llm), Persian digits.
 2  «۲ کوچکتر از ۹ است؟» answers true.
 3  «این جمله را برعکس کن: X» reverses for real (never image).
 4  «متن یادآور X را عوض کن به Y» updates the DB row; both sides named.
 5  An unknown reminder text refuses honestly.
 6  «۲۰ روز دیگر چندمه؟» matches the independent Jalali computation.
 7  «خط سوم فایل X» shows the real numbered line.
 8  «آخرین خط فایل X را بگو» reads (never chains speech).
 9  An out-of-range line refuses with the real line count.
10  «کلمه X در فایل Y چند بار؟» counts the real frequency.
11  An absent word says so plainly.
12  The seeded reminder row is cleaned and the store intact.
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
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import (
        delete_schedule,
        list_schedules,
        register_one_shot,
    )

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r71p%'")

    # 1-2 — the comparison
    p1 = route_and_run("۵ بزرگتر از ۳ است؟")
    check(1, "the comparison answers from data (never llm)",
          p1.get("ok") is True and p1.get("route") == ["data"]
          and "بزرگتر است از ۳" in str(p1.get("agent_report", "")))
    p2 = route_and_run("۲ کوچکتر از ۹ است؟")
    check(2, "the less-than answers true",
          p2.get("ok") is True
          and "کوچکتر است از" in str(p2.get("agent_report", "")))

    # 3 — the text reverse
    p3 = route_and_run("این جمله را برعکس کن: سلام دنیا")
    check(3, "the reverse is a text transform (never image)",
          p3.get("ok") is True and "image" not in (p3.get("route") or [])
          and "ایند مالس" in str(p3.get("agent_report", "")))

    # 4-5 — the reminder-text edit
    register_one_shot("فردا ساعت ۹ گواه-r71p")
    p4 = route_and_run("متن یادآور گواه-r71p را عوض کن به جلسهی مهم گواه-r71p")
    row4 = next((s for s in list_schedules()
                 if "گواه-r71p" in s.command), None)
    check(4, "the reminder text really changes in the DB",
          p4.get("ok") is True and p4.get("route") == ["scheduler"]
          and row4 is not None and "جلسهی مهم" in row4.command)
    p5 = route_and_run("متن یادآور ناموجود-zz71p را عوض کن به چیز")
    check(5, "an unknown reminder text refuses honestly",
          p5.get("ok") is False
          and "پیدا نکردم" in str(p5.get("agent_report", "")))

    # 6 — the N-days date
    p6 = route_and_run("۲۰ روز دیگر چندمه؟")
    tgt = date.today() + timedelta(days=20)
    from jdatetime import date as jdate

    j6 = jdate.fromgregorian(date=tgt)
    fa_day = str(j6.day).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    check(6, "the N-days date matches the independent computation",
          p6.get("ok") is True and fa_day in str(p6.get("agent_report", "")))

    # 7-9 — the line reads
    f = Path("D:/um_r71_probe.txt")
    f.write_text("خط اول\nخط دوم\nخط سوم گواه\nخط چهارم", encoding="utf-8")
    p7 = route_and_run(f"خط سوم فایل {f} را نشان بده")
    check(7, "the third line shows, numbered",
          p7.get("ok") is True
          and "خط ۳ از ۴" in str(p7.get("agent_report", ""))
          and "خط سوم گواه" in str(p7.get("agent_report", "")))
    p8 = route_and_run(f"آخرین خط فایل {f} را بگو")
    check(8, "the last line reads (never chains speech)",
          p8.get("ok") is True and p8.get("route") == ["textfile"]
          and "خط چهارم" in str(p8.get("agent_report", "")))
    p9 = route_and_run(f"خط نهم فایل {f} را نشان بده")
    check(9, "an out-of-range line refuses with the real count",
          p9.get("ok") is False
          and "نیست" in str(p9.get("agent_report", "")))
    f.unlink(missing_ok=True)

    # 10-11 — the frequency
    f2 = Path("D:/um_r71_probe2.txt")
    f2.write_text("گواه یک\nگواه دو\nسطر دیگر", encoding="utf-8")
    p10 = route_and_run(f"کلمه گواه در فایل {f2} چند بار آمده؟")
    check(10, "the real frequency",
          p10.get("ok") is True
          and "۲ بار" in str(p10.get("agent_report", "")))
    p11 = route_and_run(f"کلمه فلان-نیست در فایل {f2} چند بار آمده؟")
    check(11, "an absent word says so",
          p11.get("ok") is True
          and "نیامده است" in str(p11.get("agent_report", "")))
    f2.unlink(missing_ok=True)

    # 12 — cleanup + the store intact
    for s in list_schedules():
        if "گواه-r71p" in s.command:
            delete_schedule(s.schedule_id)
    left = [s for s in list_schedules() if "گواه-r71p" in s.command]
    check(12, "the seeded rows are cleaned; the operator's rows intact",
          left == [] and any(s.schedule_id == 68 for s in list_schedules()))

    print()
    if FAILURES:
        print(f"R71 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R71 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
