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


def tick() -> dict[str, object]:
    """One honest tick: fire everything due through the real engine."""
    from universal_mind.scheduler import run_due

    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = run_due()
    fired = result.get("fired", [])
    print(f"[{stamp}] tick: {result.get('count', 0)} schedule(s) fired")
    for entry in fired:
        status = "OK" if entry.get("ok") else f"FAILED ({entry.get('error', '')[:60]})"
        print(f"  - {entry.get('command', '')[:60]} → {status}")
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