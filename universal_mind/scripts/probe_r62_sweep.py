#!/usr/bin/env python3
"""R62 — the remaining-classes sweep's fixes, live-proved: 12 proofs.

The 17-command sweep measured 1 OK / 16 gaps; T1-T5 closed the six
classes. This probe re-runs the REAL sentences:

 1  «جلسه شنبه ساعت ۱۰ است — یادت باشد» registers an appointment
    (trailing marker; weekday distance).
 2  The weekday distance matches an independent computation.
 3  «شنبه آینده» is strictly the next cycle.
 4  «قرارهایم را نشان بده» answers from the real agenda.
 5  «هوا تهران چطوره؟» is a NAMED refusal (world-data), never a guess.
 6  The knowledge refusal offers both real roads.
 7  «قیمت طلا چنده؟» never answers with a number.
 8  «خلاصه کن این متن را: …» summarizes with the text's own sentences.
 9  The summary report counts honestly (picked from total).
10  «کندتر حرف بزن» changes the remembered rate (and teaches the way back).
11  «لغو کن» refuses honestly and names the last real run.
12  A reminder run leaves a run_history row (the silence bug is closed).
"""

from __future__ import annotations

import os
import re
import sys
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
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import parse_one_shot
    from universal_mind.database_suite import DatabaseSuite

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    # 1-3 — appointments
    r1 = report("جلسه شنبه ساعت ۱۰ است — یادت باشد")
    check(1, "the weekday appointment registers", "ثبت شد" in r1)
    parsed = parse_one_shot("جلسه شنبه ساعت ۱۰ است")
    real = next(d for d in range(8)
                if (datetime.now() + timedelta(days=d)).weekday() == 5)
    check(2, f"شنبه distance matches independent math ({parsed['day_offset']} vs {real})",
          parsed["day_offset"] == real)
    p3 = parse_one_shot("جلسه شنبه آینده ساعت ۱۰ است")
    real3 = next(d for d in range(1, 15)
                 if (datetime.now() + timedelta(days=d)).weekday() == 5)
    check(3, "«آینده» forces the next cycle", p3["day_offset"] == real3)
    DatabaseSuite(persistent=True).execute(
        "DELETE FROM schedules WHERE command LIKE '%جلسه شنبه%'")

    # 4 — the appointments view
    r4 = report("قرارهایم را نشان بده")
    check(4, "«قرارهایم» opens the agenda", "برنامه" in r4 or "قرار" in r4)

    # 5-7 — knowledge questions
    r5 = report("هوا تهران چطوره؟")
    check(5, "the weather question is refused with the topic named",
          "«هوا»" in r5 and "دادهٔ بیرونی" in r5)
    check(6, "both real roads are offered",
          "هوش مصنوعی" in r5 and "سایت" in r5)
    r7 = report("قیمت طلا چنده؟")
    check(7, "the gold price is never a fabricated number",
          "نتیجه" not in r7 and "حدسی نمی‌سازم" in r7)

    # 8-9 — the summary capability
    text = ("هوش مصنوعی در سالهای اخیر تغییر بزرگی کرده است. ماشینها حالا متن را میخوانند. "
            "در ایران روی زبان فارسی کار میشود. چالشهای فارسی خاص است. آینده روشن است.")
    r8 = report(f"خلاصه کن این متن را: {text}")
    check(8, "the summary selects the text's own sentences",
          "خلاصه" in r8 and "هوش مصنوعی در سالهای اخیر" in r8)
    m9 = re.search(r"(\d+) جمله از (\d+)", r8.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
    check(9, "the summary counts honestly (picked from total)",
          m9 is not None and m9.group(1) == "3" and int(m9.group(2)) == 5)

    # 10 — speech accessibility
    from universal_mind import operator_preferences as op

    op.set("speech_rate", "0")
    r10 = report("کندتر حرف بزن")
    check(10, "the remembered pace steps down",
          int(op.get("speech_rate") or 0) == -2 and "کندتر" in r10)
    op.set("speech_rate", "0")

    # 11-12 — cancel and the history row
    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM run_history WHERE command LIKE '%جلسه شنبه%'")
    route_and_run("یادم باشه پس‌فردا ساعت ۶ گواه-r62-probe")
    q = db.query("SELECT COUNT(*) n FROM run_history WHERE command LIKE '%گواه-r62-probe%'")
    n12 = int(q["rows"][0]["n"]) if q.get("ok") else 0
    check(12, "a reminder run leaves its history row", n12 >= 1)
    r11 = report("لغو کن")
    check(11, "cancel refuses honestly and names the last run",
          "لغوِ خودکار نمی‌کنم" in r11 and "گواه-r62-probe" in r11)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r62-probe%'")
    db.execute("DELETE FROM run_history WHERE command LIKE '%گواه-r62-probe%'")

    print()
    if FAILURES:
        print(f"R62 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R62 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
