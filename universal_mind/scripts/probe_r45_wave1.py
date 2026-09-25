#!/usr/bin/env python3
"""Probe: R45 wave-1 — time memory, live (yesterday/week/month + reminder + chat).

The operator's questions reach back in time now. This probe walks the REAL
paths end-to-end: the seeded store answers each time window with real counts
(the LOCAL-day law, honest refusals excluded), «یادآور + زمان» registers a
real schedule row with half-hour precision, and the chat replays from the
real table. Every claim printed comes from a live call, never a mock.
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PARENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PARENT))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402
from universal_mind.run_history import RunHistory  # noqa: E402
from universal_mind.scheduler import _ensure_table  # noqa: E402


def main() -> int:
    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe_r45w1.db"))
    RunHistory(db)
    _ensure_table(db)
    now = dt.datetime.now()
    for back, ok, cls in (
        (0, 1, ""), (0, 1, ""), (1, 1, ""), (1, 0, ""),
        (3, 1, ""), (40, 1, ""), (40, 1, "blocked_env"),
    ):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('probe-seed','data',{int(ok)},1.0,'{cls}','{ts}')"
        )

    with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
        from universal_mind.persian_router import route_and_run

        print("== R45-1 time windows (seeded store, LOCAL-day law):")
        for q in ("دیروز چی کار کردی؟", "این هفته چطور بود؟",
                  "ماه پیش چطور بود؟", "هفته پیش چه بود؟"):
            p = route_and_run(q)
            print(f"  «{q}» → {p['route']} | {p['agent_report']}")
        checks: list[tuple[str, bool]] = []

        p = route_and_run("دیروز چی کار کردی؟")
        checks.append(("دیروز = ۲ فرمان/۱ موفق",
                       "۲ فرمان" in p["agent_report"] and "۱ موفق" in p["agent_report"]))
        p = route_and_run("این هفته چطور بود؟")
        checks.append(("هفته = ۵/۴", "۵ فرمان" in p["agent_report"] and "۴ موفق" in p["agent_report"]))
        p = route_and_run("هفته پیش چه بود؟")
        checks.append(("هفتهی پیش سکوت صادقانه", "سکوت" in p["agent_report"]))

        print("== R45-2 the daily reminder (half-hour precision):")
        p = route_and_run("هر روز ساعت ۸ و نیم یادآور کن گزارش هفتگی را بفرست")
        print(f"  «...۸ و نیم...» → {p['route']} | {p['agent_report']}")
        checks.append(("یادآورِ نیمساعته ثبت شد",
                       p["route"] == ["scheduler"] and "۸:۳۰" in p["agent_report"]))
        p = route_and_run("یادآور کن گزارش بده")
        checks.append(("یادآور بدون زمان = همان مسیر قدیمی",
                       p["route"] != ["scheduler"]))

        from universal_mind.scheduler import list_schedules
        scheds = [s for s in list_schedules() if s.hour_of_day == 8]
        checks.append(("ردیف واقعی h=8 m=30", bool(scheds) and scheds[0].minute_of_hour == 30))

        print("== R45-3 chat memory:")
        from universal_mind.chat_history_store import log_message
        log_message("من", "نمودار فروش را بکش", ok=True)
        log_message("سیستم", "نمودار ساخته شد", ok=True)
        p = route_and_run("آخرین گفتگویمان چه بود؟")
        print(f"  «آخرین گفتگویمان چه بود؟» → {p['agent_report'].splitlines()[0]}")
        checks.append(("گفتگو بازپخش شد",
                       "نمودار فروش را بکش" in p["agent_report"] and "۲ پیام" in p["agent_report"]))

        print("== R45-4 red team (time-passage hostility, 14 commands):")
        from universal_mind.red_team import run_red_team
        r = run_red_team()
        print(f"  total={r['total']} honest={r['honest']} findings={len(r['findings'])}")
        checks.append(("پیکرهی خصمانه ۱۶تایی → ۱۴/۱۴ صادق",
                       r["total"] == 14 and r["honest"] == 14 and not r["findings"]))

    print()
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"R45-W1: {'ALL HOLDS GREEN' if not failed else 'FAILED: ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
