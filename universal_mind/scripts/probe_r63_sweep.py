#!/usr/bin/env python3
"""R63 — the compound-sentence sweep's fixes, live-proved: 10 proofs.

The 15-command sweep measured 8 classes of gap; P1-P8 closed them.
This probe re-runs the REAL sentences end-to-end:

 1  The big teach sentence no longer poisons the route overlay
    (nothing stored; the overlay stays clean).
 2  A real small definition still teaches, and the next sentence
    routes through the taught word.
 3  «فایل گزارش.md بساز و داخلش بنویس …» creates the REAL file with
    the exact content (then cleans up).
 4  A dataless chart is a named refusal with both roads.
 5  Numbers in the sentence still draw a real chart.
 6  A close command for a non-existent window refuses with the real
    open list (and closes nothing).
 7  A RAM-floor question answers the FILTER, not the generic top-5.
 8  «متغیر محیطی TEMP را نشان بده» shows the real value.
 9  A secret-looking env name is masked, never printed.
10  «برنامه هفته آینده من چیست؟» reaches the agenda, not the LLM.
"""

from __future__ import annotations

import os
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
    os.environ["UM_MUTE"] = "1"
    os.environ["UM_R63_PROBE_TOKEN"] = "never-print-me"
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    # 1-2 — the teach gate
    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM learned_vocab WHERE word IN ('زرشک', 'رفت', 'برق')")
    report("یک قابلیت جدید یاد بگیر: وقتی گفتم برق رفت یعنی برق وایرلس قطع شد")
    q = db.query("SELECT COUNT(*) n FROM learned_vocab WHERE word = 'رفت'")
    n1 = int(q["rows"][0]["n"]) if q.get("ok") else -1
    check(1, "the big teach sentence stores nothing (overlay clean)", n1 == 0)
    report("واژهی زرشک یعنی داده")
    rep2 = report("میانگین زرشک و ۴ و ۶ را حساب کن")
    check(2, "a real definition teaches and the next sentence routes",
          "زرشک" not in rep2 and ("میانگین" in rep2 or "برابر" in rep2))
    db.execute("DELETE FROM learned_vocab WHERE word = 'زرشک'")

    # 3 — the compound file sentence
    target = Path.home() / "Documents" / "universal_mind" / "گزارش-r63-probe.md"
    target.unlink(missing_ok=True)
    rep3 = report("فایل گزارش-r63-probe.md را بساز و داخلش بنویس این گواهِ probe است")
    exists = target.exists()
    content = target.read_text(encoding="utf-8") if exists else ""
    target.unlink(missing_ok=True)
    check(3, "the compound sentence creates the real file with the content",
          exists and content == "این گواهِ probe است" and "نوشتم" in rep3)

    # 4-5 — the chart honesty
    rep4 = report("نمودار خطی از فروش ماهانه را بکش")
    check(4, "a dataless chart is a named refusal with both roads",
          "نمودار بدون داده" in rep4 and "بکش" in rep4)
    rep5 = report("نمودار خطی از ۱ و ۴ و ۹ بکش")
    check(5, "numbers in the sentence draw a real chart",
          "در «" in rep5 and ".png" in rep5)

    # 6 — the window close refusal (nothing gets closed)
    rep6 = report("پنجره‌های برنامه-آزمون-ناموجود-r63 را ببند")
    check(6, "a non-existent window refuses with the real open list",
          "باز نیست" in rep6 and "پنجره‌های دیده‌شده" in rep6)

    # 7 — the RAM filter
    rep7 = report("کدام پروسه‌ها بیشتر از ۱ گیگ رم می‌خورند؟")
    check(7, "the RAM floor answers the FILTER, never the generic top-5",
          "مرتب بر CPU" not in rep7
          and ("هیچ پردازشی" in rep7 or "پردازش بیش از" in rep7))

    # 8-9 — the env var view
    rep8 = report("متغیر محیطی TEMP را نشان بده")
    check(8, "TEMP shows its real value", "متغیر محیطی TEMP = " in rep8)
    rep9 = report("متغیر محیطی UM_R63_PROBE_TOKEN را نشان بده")
    check(9, "a secret-looking env name is masked, never printed",
          "never-print-me" not in rep9 and "مخفی" in rep9)

    # 10 — the week agenda
    rep10 = report("برنامه هفته آینده من چیست؟")
    check(10, "the week question reaches the agenda, not the LLM",
          ("برنامه" in rep10 or "قرار" in rep10)
          and "مدل زبانی" not in rep10)

    print()
    if FAILURES:
        print(f"R63 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R63 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
