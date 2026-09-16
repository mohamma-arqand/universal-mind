#!/usr/bin/env python3
"""The proactive tick — fire every due schedule, then sleep until the next.

Run mode (default): one tick then exit (safe for a Windows Task Scheduler job
or an external cron — the process never lingers).

    python scripts/scheduler_tick.py            # one tick
    python scripts/scheduler_tick.py --loop 60   # every 60s, forever (Ctrl+C)

The tick is idempotent and honest: it fires ONLY what is due, records each
firing (even failures advance the clock), and prints exactly what ran.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def tick(*, notify_summary: bool = True) -> dict[str, object]:
    """One honest tick: fire everything due, then SAY what ran.

    With ``notify_summary`` the tick closes its own perception loop: a real
    Windows toast reports how many scheduled tasks fired and how they went —
    the operator learns the platform worked while away, without opening it.
    """
    from universal_mind.scheduler import run_due

    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = run_due()
    fired = result.get("fired", [])
    count = result.get("count", 0)
    print(f"[{stamp}] tick: {count} schedule(s) fired")
    for entry in fired:
        status = "OK" if entry.get("ok") else f"FAILED ({entry.get('error', '')[:60]})"
        print(f"  - {entry.get('command', '')[:60]} → {status}")

    if notify_summary and count:
        ok_count = sum(1 for f in fired if f.get("ok"))
        failed = count - ok_count
        # Persian digits, honest wording — successes first, failures named.
        fa = str(count).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        fa_ok = str(ok_count).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        body = f"{fa} کارِ زمان‌بندی‌شده اجرا شد ({fa_ok} موفق)"
        if failed:
            fa_failed = str(failed).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            body += f"، {fa_failed} ناموفق"
        try:
            from universal_mind.real_notify import NotifyTool

            NotifyTool().notify(title="ذهن یکپارچه — اجرای خودکار", body=body)
        except Exception as exc:  # noqa: BLE001 — the toast is a bonus, never fatal
            print(f"(toast failed: {exc})")
    return dict(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="The proactive scheduler tick")
    parser.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                        help="keep ticking every SECONDS (0 = one tick and exit)")
    args = parser.parse_args()

    if args.loop <= 0:
        tick()
        return 0

    print(f"watching: a tick every {args.loop}s (Ctrl+C to stop)")
    try:
        while True:
            tick()
            time.sleep(args.loop)
    except KeyboardInterrupt:
        print("stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())