#!/usr/bin/env python3
"""R79 — the CATEGORY-GAPS sweep (wave 2): 10 live proofs.

Meeting placement (قرار بگذار + the fact-stated shape) and the window
listing — both died in «نشناختم» in the audit. Plus the wave-1 refusals
re-verified together (one product, one view).
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

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r79p%'")

    # 1-3 — meeting placement
    p = route_and_run("قرار بگذار شنبه ساعت ۱۰ جلسه گواه-r79p")
    rep = str(p.get("agent_report", ""))
    check(1, f"«قرار بگذار …» registers ({p.get('route')})",
          p.get("ok") is True and p.get("route") == ["scheduler"]
          and "قرار ثبت شد" in rep)
    p = route_and_run("فردا ساعت ۹ جلسه گواه-r79p دارم")
    rep = str(p.get("agent_report", ""))
    check(2, "the fact-stated shape registers too",
          p.get("ok") is True and "قرار ثبت شد" in rep)
    p = route_and_run("قرار بگذار جلسه گواه-r79p")
    check(3, "a timeless placement is a NAMED refusal",
          p.get("ok") is False and "زمانِ قرار" in str(p.get("agent_report", "")))

    # 4-6 — the window listing
    p = route_and_run("لیست پنجرههای باز")
    rep = str(p.get("agent_report", ""))
    check(4, f"the window list is reflexive ({p.get('route')})",
          p.get("route") == ["reflexive"])
    check(5, "…with REAL windows and NO mangled titles",
          ("پنجره باز" in rep) and ("??" not in rep))
    p = route_and_run("پنجرهای باز نیست؟")
    check(6, "the colloquial question shape answers too",
          p.get("ok") is True and "پنجره" in str(p.get("agent_report", "")))

    # 7-8 — the wave-1 refusals hold together
    p = route_and_run("یه موسیقی قشنگ پخش کن")
    check(7, "the play refusal holds",
          p.get("ok") is False and "پخشکننده" in str(p.get("agent_report", "")))
    p = route_and_run("ویروس اسکن کن")
    check(8, "the security refusal holds",
          p.get("ok") is False and "Defender" in str(p.get("agent_report", "")))

    # 9-10 — the neighbours survive
    p = route_and_run("یادآورهای من")
    check(9, "the plain reminder list survives",
          p.get("ok") is True and "یادآورهایت" in str(p.get("agent_report", "")))
    p = route_and_run("چند تا یادآور داری؟")
    check(10, "the count ask still never registers (Δ-0 law)",
          p.get("route") == ["reflexive"] and "یادآور داری" in str(p.get("agent_report", "")))

    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r79p%'")
    print()
    if FAILURES:
        print(f"R79-2 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R79-2 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
