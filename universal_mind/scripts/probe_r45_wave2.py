#!/usr/bin/env python3
"""Probe: R45 wave-2 — the dashboard's full face + the weekly letter, live.

Every R44/R45 signal now has a HOUSE on the dashboard: the pulse (7-day
streak, silent days in Jalali), the drift (hot-path ratio vs the committed
baseline), and the human loop (verdicts + red-team findings). And the
platform writes its own week unprompted: the first tick of each ISO week
renders a real Persian letter — runs, successes, best route, verdicts —
into a weekly_reports row «گزارش هفته چطور بود؟» reads back. All claims
printed come from live calls on a seeded store.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PARENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PARENT))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402
from universal_mind.run_history import RunHistory  # noqa: E402


def main() -> int:
    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe_r45w2.db"))
    RunHistory(db)
    now = dt.datetime.now()
    for back, ok in ((0, 1), (1, 1), (2, 0), (5, 1)):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('probe-seed','data',{ok},1.0,'','{ts}')"
        )
    checks: list[tuple[str, bool]] = []

    with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
        # — the three new houses —
        from universal_mind.superplatform_dashboard import build_dashboard

        out = Path(tempfile.mkdtemp()) / "probe.html"
        r = build_dashboard(str(out))
        html = Path(str(r["path"])).read_text(encoding="utf-8")
        print("== R45-5/6/7 the dashboard's new houses (seeded store):")
        m = re.search(r"رشتهی تپش: ([^<]+)<", html)
        pulse = m.group(1) if m else ""
        print(f"  pulse house: {pulse}")
        checks.append(("خانهی تپش: رشته + روزهای سکوت", "روز پیوسته" in pulse))
        m = re.search(r"hot path ([^<]+)<", html)
        drift = m.group(1) if m else ""
        print(f"  drift house: {drift}")
        checks.append(("خانهی رانش: نسبتِ مبنا→الان", "مبنا" in drift and "×" in drift))
        m = re.search(r"رأیها: ([^<]+)", html)
        human = m.group(1) if m else ""
        print(f"  human house: {human}")
        checks.append(("خانهی حلقهی انسانی: رأیها + یافتهها", "👍" in human))

        # — the weekly letter —
        from universal_mind.weekly_letter import (
            due_this_week,
            latest_letter,
            record_weekly_letter,
        )

        print("== R45-8 the weekly letter:")
        checks.append(("هفته بدون نامه → سرسیددار", due_this_week() is True))
        info = record_weekly_letter()
        print(f"  letter: {info['report']}")
        # the letter DERIVES from the real week: the golden-corpus drift
        # sweep inside the dashboard adds its own live rows, so the probe
        # asserts the letter's shape and that the seed is INCLUDED (>=4).
        n_m = re.search(r"(\d+) فرمان", info["report"])
        n = int(n_m.group(1)) if n_m else 0
        checks.append(("نامه از هفتهی واقعی", n >= 4 and "٪" in info["report"] and "پرکاربردترین مسیر" in info["report"]))
        checks.append(("بعد از نامه → سرسیددار نیست", due_this_week() is False))
        stored = latest_letter()
        checks.append(("خواندن نامهی ذخیرهشده", stored["ok"] and stored["report"] == info["report"]))

        from universal_mind.persian_router import route_and_run

        p = route_and_run("گزارش هفته چطور بود؟")
        print(f"  asked → {p['route']} | {p['agent_report'][:70]}")
        checks.append(("پرسش گفتاری → خود نامه", p["route"] == ["reflexive"] and "نامهی هفته" in p["agent_report"]))

    print()
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"R45-W2: {'ALL HOLDS GREEN' if not failed else 'FAILED: ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
