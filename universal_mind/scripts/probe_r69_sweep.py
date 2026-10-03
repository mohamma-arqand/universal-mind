#!/usr/bin/env python3
"""R69 — the compound-time/sorting/word-numbers sweep's fixes, live: 12 proofs.

 1  «یک ساعت دیگر یادم بیار …» registers NOW+60 (never a PDF).
 2  «نیم ساعت دیگر» = 30 minutes.
 3  «بیست و پنج دقیقه دیگر» = 25 minutes (the word-number rides).
 4  «ساعت ۸:۳۰ فردا» lands at 08:30 tomorrow.
 5  A reminder verb never builds a document (the pdf word steps aside).
 6  «چند درصد باتری مانده؟» answers the machine's vitals, never a mean.
 7  «مرتب کن: ۵ و ۲ و ۹» sorts ascending (Persian digits).
 8  «ترتیب نزولی …» sorts descending.
 9  «بزرگترین از ۵ و ۹ و ۲؟» answers 9 as a DATA question (never llm).
10  «کوچکترین از …» answers 2.
11  «بیست و پنج بعلاوه هفت چنده؟» = 32 (word-numbers in compute).
12  The word-boundary law holds («چنده» yields no phantom 10).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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
    from universal_mind.persian_params import extract_numbers
    from universal_mind.persian_router import route, route_and_run
    from universal_mind.scheduler import list_schedules, parse_one_shot

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%-r69p%'")

    # 1 — the relative hour registers (and never a PDF)
    p1 = route_and_run("یک ساعت دیگر یادم بیار گزارش بده-r69p")
    row = next((s for s in list_schedules() if "گزارش بده-r69p" in s.command), None)
    fire = datetime.fromisoformat(row.run_at) if row else None
    delta = ((fire - datetime.now()).total_seconds() / 60) if fire else -1
    check(1, "«یک ساعت دیگر» registers NOW+60 (never a PDF)",
          p1.get("ok") is True and p1.get("route") == ["scheduler"]
          and 55 <= delta <= 65)

    # 2-4 — the compound parsers
    s2 = parse_one_shot("نیم ساعت دیگر یادم بیار زنگ بزن")
    check(2, "«نیم ساعت دیگر» = 30 minutes",
          s2 is not None and s2.get("relative_minutes") == 30)
    s3 = parse_one_shot("بیست و پنج دقیقه دیگر زنگ بزن")
    check(3, "«بیست و پنج دقیقه دیگر» = 25 minutes (word-number)",
          s3 is not None and s3.get("relative_minutes") == 25)
    s4 = parse_one_shot("ساعت ۸:۳۰ فردا یادم بیار جلسه-r69p")
    fire4 = datetime.fromisoformat(s4["run_at"]) if s4 else None
    check(4, "«ساعت ۸:۳۰ فردا» lands at 08:30 tomorrow",
          fire4 is not None and fire4.hour == 8 and fire4.minute == 30)

    # 5 — the ownership
    caps5 = route("یک ساعت دیگر یادم بیار گزارش بده").capabilities
    check(5, "a reminder verb never builds a document", "pdf" not in caps5)

    # 6 — the battery vital
    p6 = route_and_run("چند درصد باتری مانده؟")
    rep6 = str(p6.get("agent_report", ""))
    check(6, "the battery question answers the machine's vitals",
          p6.get("route") == ["sysstatus"] and "میانگین" not in rep6
          and "روشن است" in rep6)

    # 7-10 — the sort and the extremes
    p7 = route_and_run("مرتب کن: ۵ و ۲ و ۹")
    check(7, "ascending sort, Persian digits",
          p7.get("ok") is True and "۲، ۵، ۹" in str(p7.get("agent_report", "")))
    p8 = route_and_run("ترتیب نزولی ۵ و ۲ و ۹ را نشان بده")
    check(8, "descending sort",
          p8.get("ok") is True and "۹، ۵، ۲" in str(p8.get("agent_report", "")))
    p9 = route_and_run("بزرگترین از ۵ و ۹ و ۲ چیست؟")
    check(9, "the largest is a DATA question answering 9",
          p9.get("route") == ["data"]
          and "بزرگترین از ۳ عدد: ۹" in str(p9.get("agent_report", "")))
    p10 = route_and_run("کوچکترین از ۵ و ۹ و ۲ چیست؟")
    check(10, "the smallest answers 2",
          p10.get("ok") is True
          and "کوچکترین از ۳ عدد: ۲" in str(p10.get("agent_report", "")))

    # 11-12 — the word-numbers
    p11 = route_and_run("بیست و پنج بعلاوه هفت چنده؟")
    check(11, "«بیست و پنج بعلاوه هفت» = 32",
          p11.get("ok") is True and "نتیجه ۳۲" in str(p11.get("agent_report", "")))
    check(12, "the word-boundary law holds (no phantom 10 in «چنده»)",
          extract_numbers("بیست و پنج بعلاوه هفت چنده؟") == [25.0, 7.0])

    # cleanup
    db.execute("DELETE FROM schedules WHERE command LIKE '%-r69p%'")

    print()
    if FAILURES:
        print(f"R69 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R69 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
