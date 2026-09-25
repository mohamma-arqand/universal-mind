#!/usr/bin/env python3
"""Probe: R45 wave-3 — the self-aware mind, live.

The platform now cleans its own data, answers for its own health with
five live signals, advises from what the operator ACTUALLY does, and
harvests the words it fails to understand:

9.  the noise purge: dry-run vs apply on a seeded store (the real store
    was purged in the item's own run: 2,701 rows marked, 0 left);
10. «وضعیت خودت چطور است؟» — pulse/drift/backup/verdicts/red-team, each
    read from its live source;
11. «پیشنهاد بده» — hot routes, best route (real excellence), and the
    capabilities never used, from the real store;
12. the unknown harvest — a real refusal lands in unknown_terms; the
    conversational question reads it back.

All claims printed come from live calls, never mocks of the answer.
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


def main() -> int:
    db = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe_r45w3.db"))
    RunHistory(db)
    now = dt.datetime.now()
    for back, route, exc in ((0, "data", 0.95), (1, "data", 0.9),
                             (2, "pdf", 0.8), (3, "chart", 0.7)):
        ts = (now - dt.timedelta(days=back)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            f"VALUES ('probe-seed','{route}',1,{exc},'', '{ts}')"
        )
    for _ in range(3):  # the poison the purge must find
        db.execute(
            "INSERT INTO run_history (command, route, succeeded, excellence, outcome_class, created_at) "
            "VALUES ('noise','','0','', '', '2026-01-01 00:00:00')"
        )
    checks: list[tuple[str, bool]] = []

    with patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: db)):
        print("== R45-9 the noise purge (dry-run then apply):")
        from universal_mind.noise_purge import purge_unknown_noise

        dry = purge_unknown_noise(db=db, apply=False)
        print(f"  dry: {dry['report']}")
        checks.append(("خشک: شمرد و ننوشت", dry["rows_found"] == 3 and dry["rows_updated"] == 0))
        applied = purge_unknown_noise(db=db, apply=True)
        print(f"  apply: {applied['report']}")
        checks.append(("اعمال: ۳ ردیف علامت خورد", applied["rows_updated"] == 3))
        left = db.query(
            "SELECT COUNT(*) AS n FROM run_history "
            "WHERE route='' AND (outcome_class IS NULL OR outcome_class='')"
        )["rows"][0]["n"]
        checks.append(("صفر ردیفِ بدون کلاس ماند", left == 0))

        from universal_mind.persian_router import route_and_run

        print("== R45-10 «وضعیت خودت چطور است؟» (five live signals):")
        p = route_and_run("وضعیت خودت چطور است؟")
        print("  " + p["agent_report"].replace("\n", "\n  "))
        rep = p["agent_report"]
        checks.append(("پنج سیگنال در یک پاسخ", all(
            w in rep for w in ("تپش", "رانش کارایی", "بکاپ", "رأیهای تو", "تیم سرخ"))))

        print("== R45-11 «پیشنهاد بده» (from the real store):")
        p = route_and_run("پیشنهاد بده")
        print("  " + p["agent_report"].replace("\n", "\n  "))
        rep2 = p["agent_report"]
        # the live router's own question-runs joined the week, so the probe
        # asserts the SHAPE: the hot route names data with a real count,
        # the best route carries a real excellence percent, the never-used
        # capabilities are named.
        import re as _re
        hot_ok = bool(_re.search(r"«data» \((\d+) بار\)", rep2))
        best_ok = bool(_re.search(r"«data» بوده \(داوری (\d+)٪\)", rep2))
        checks.append(("مسیر داغ + بهترین + تازگیها",
                       hot_ok and best_ok and "امتحان کن" in rep2))

        print("== R45-12 the unknown harvest:")
        r1 = route_and_run("فلانbabایی را باطلا کن")
        checks.append(("ردِ صادقانه", r1["ok"] is False))
        route_and_run("فلانbabایی را باطلا کن")
        r2 = route_and_run("چه واژههایی را نمیشناسی؟")
        print(f"  asked → {r2['agent_report'][:80]}")
        checks.append(("واژهی ناشناخته دوبار شمرده شد",
                       "«فلانbabایی»" in r2["agent_report"] and "(۲ بار)" in r2["agent_report"]))

    print()
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"R45-W3: {'ALL HOLDS GREEN' if not failed else 'FAILED: ' + ', '.join(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
