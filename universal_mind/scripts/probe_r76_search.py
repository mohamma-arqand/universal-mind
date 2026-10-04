#!/usr/bin/env python3
"""R76 — the REMINDER-QUESTION sweep: 10 live proofs.

A 14-command sweep found 8 wrong answers — the worst: a COUNT ask
REGISTERED a new reminder. The class: question words close the
registration gate; counting/extremes/search/sort answer from the REAL
schedules table.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    os.environ["UM_MUTE"] = "1"

    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import list_schedules, register_one_shot

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r76p%'")
    register_one_shot("فردا ساعت ۹ جلسه گواه-r76p")

    # 1-2 — a question NEVER registers
    n0 = len(list_schedules())
    p = route_and_run("چند تا یادآور برای فردا داری؟")
    check(1, f"the count ask answers reflexively ({p.get('route')})",
          p.get("route") == ["reflexive"] and p.get("ok") is True)
    check(2, f"and registers NOTHING (Δ={len(list_schedules()) - n0})",
          len(list_schedules()) == n0)

    # 3-4 — the extremes answer from the table, not chain statistics
    rep = str(route_and_run("بزرگترین یادآور من کدام است؟").get("agent_report", ""))
    check(3, "«بزرگترین یادآور» names the longest row",
          "بلندترین یادآورت" in rep and "موفقترین" not in rep)
    rep = str(route_and_run("آخرین یادآورم چی بود؟").get("agent_report", ""))
    check(4, "«آخرین یادآورم» names the newest row",
          "جدیدترین یادآورت" in rep and "وضعیت سیستم" not in rep)

    # 5-6 — search + sort inside the reminders
    rep = str(route_and_run("در یادآورهایم دنبال جلسه بگرد").get("agent_report", ""))
    check(5, "search inside reminders finds the probe row",
          "یادآور با «جلسه»" in rep and "گواه-r76p" in rep)
    p = route_and_run("یادآورهایم را بر اساس زمان مرتب کن")
    rep = str(p.get("agent_report", ""))
    check(6, "sorting lists the real rows (never the ۲،۴ data mean)",
          p.get("ok") is True and "به ترتیب" in rep and "مرتب شد (صعودی)" not in rep)

    # 7-8 — the real registrations survive
    n1 = len(list_schedules())
    p = route_and_run("یادم بنداز که پس‌فردا ساعت ۷ گواه-r76p جلسه دوم")
    check(7, "a real registration still registers",
          p.get("ok") is True and "scheduler" in p["route"]
          and len(list_schedules()) == n1 + 1)
    p = route_and_run("یادآورهای من")
    rep = str(p.get("agent_report", ""))
    check(8, "the plain list still lists",
          p.get("ok") is True and "یادآورهایت" in rep)

    # 9-10 — count + oldest from the real table
    rep = str(route_and_run("چند تا یادآور داری؟").get("agent_report", ""))
    check(9, "the total count answers", "یادآور داری" in rep)
    rep = str(route_and_run("قدیمیترین یادآور من کدام است؟").get("agent_report", ""))
    check(10, "the oldest is named (with its time)",
          "قدیمیترین یادآورت" in rep)

    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r76p%'")
    print()
    if FAILURES:
        print(f"R76 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R76 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
