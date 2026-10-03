#!/usr/bin/env python3
"""R68 — the self-awareness sweep's fixes, live: 12 proofs.

The 15-question read-only sweep measured 8 gaps — two LIVE WRONG
ANSWERS (a contact count answered with the RUN count; system stats
answered with the extracted_data table's experimental average).
P1-P7 closed them. This probe re-runs the REAL questions:

 1  «آمار کل سیستم» routes to sysstatus ALONE (never data:stats).
 2  The live answer is the machine's vitals (uptime/RAM), never a mean.
 3  «چند تا مخاطب داری؟» counts the REAL book (seeded + counted).
 4  The contact count never answers with the run count.
 5  «وضعیت کلی من چطور است؟» is today's review, never the goal board.
 6  «چه مدت است روشن نیستم؟» answers the real gap.
 7  «چه چیزهایی بلد نیستی؟» names the llm and live-data gaps.
 8  «آخرین خطای من چه بود؟» names the seeded last failed run.
 9  «مصرف امروزم چطور بوده؟» counts today's routes (the seeded one named).
10  «چند تا یادآور داری؟» still counts reminders (regression).
11  «امروز چی کارها کردی برایم؟» still answers today's work.
12  The confession keeps the no-fabrication promise.
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
    import tempfile
    from unittest.mock import patch as mock_patch

    from universal_mind.contacts import list_contacts, save
    from universal_mind.persian_router import route_and_run
    from universal_mind.run_history import RunHistory

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r68%'")
    db.execute("DELETE FROM run_history WHERE command LIKE '%گواه-r68%'")

    # 1-2 — system stats
    p1 = route_and_run("آمار کل سیستم را نشان بده")
    rep1 = str(p1.get("agent_report", ""))
    check(1, "system stats route to sysstatus alone",
          p1.get("route") == ["sysstatus"])
    check(2, "the answer is the machine's vitals, never a mean",
          "روشن است" in rep1 and "میانگین" not in rep1)

    # 3-4 — the contact count
    save("گواه-r68", "r68@example.com")
    real_n = len(list_contacts())
    p3 = route_and_run("چند تا مخاطب داری؟")
    fa_n = str(real_n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    rep3 = str(p3.get("agent_report", ""))
    check(3, "the contact count counts the real book",
          p3.get("ok") is True and f"{fa_n} مخاطب داری" in rep3)
    check(4, "the contact count never answers with the run count",
          "اجرا ثبت شده" not in rep3)

    # 5-9 — the isolated review (a real store with today's rows)
    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r68-probe.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent",
                            classmethod(lambda cls: iso)):
        RunHistory().record("گزارش گواه-r68 امروز", ["data"], True,
                           outcome_class="tool")
        RunHistory().record("خطای گواه-r68 امروز", ["chart"], False,
                            outcome_class="heuristic")
        p5 = route_and_run("وضعیت کلی من چطور است؟")
        rep5 = str(p5.get("agent_report", ""))
        check(5, "the day review answers today, never the goal board",
              p5.get("ok") is True and "وضعیت امروز" in rep5
              and "زمانبندی" not in rep5)
        p6 = route_and_run("چه مدت است روشن نیستم؟")
        rep6 = str(p6.get("agent_report", ""))
        check(6, "the since-last answer is a real gap",
              p6.get("ok") is True
              and any(w in rep6 for w in ("دقیقه", "ساعت", "ثانیه", "روز")))
        p7 = route_and_run("چه چیزهایی بلد نیستی؟")
        rep7 = str(p7.get("agent_report", ""))
        check(7, "the confession names the llm and live-data gaps",
              "مدل زبانی زنده" in rep7 and "هوای" in rep7)
        p8 = route_and_run("آخرین خطای من چه بود؟")
        rep8 = str(p8.get("agent_report", ""))
        check(8, "the last failure names the seeded run",
              p8.get("ok") is True and "خطای گواه-r68 امروز" in rep8
              and "ناموفق" in rep8)
        p9 = route_and_run("مصرف امروزم چطور بوده؟")
        rep9 = str(p9.get("agent_report", ""))
        check(9, "today's consumption counts the seeded route",
              p9.get("ok") is True and "مصرف امروز" in rep9
              and "data" in rep9)

    # 10-11 — the standing regressions
    p10 = route_and_run("چند تا یادآور داری؟")
    rep10 = str(p10.get("agent_report", ""))
    check(10, "the reminder count still counts reminders",
          p10.get("ok") is True and "یادآور" in rep10
          and "اجرا ثبت شده" not in rep10)
    p11 = route_and_run("امروز چی کارها کردی برایم؟")
    rep11 = str(p11.get("agent_report", ""))
    check(11, "today's work question still answers",
          p11.get("ok") is True and "اجرا کردم" in rep11)
    check(12, "the confession keeps the no-fabrication promise",
          "ساختگی" in str(route_and_run("چه چیزهایی بلد نیستی؟")
                          .get("agent_report", "")))

    # cleanup
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r68%'")
    db.execute("DELETE FROM run_history WHERE command LIKE '%گواه-r68%'")

    print()
    if FAILURES:
        print(f"R68 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R68 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
