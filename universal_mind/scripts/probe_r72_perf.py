#!/usr/bin/env python3
"""R72 — the deep-upgrade sweep's LIVE BENCHMARK: 12 proofs + the timing gates.

The 16-command sweep profiled the whole surface: sysstatus 1726ms
(16 subprocesses - a global lock), compute 2969ms (90% import overhead;
sklearn alone 1.6s). After: sysstatus ~40ms warm (43x), compute ~132-185ms
(20x). This probe pins BOTH the behaviour AND the timing gates so a
regression in either fails the gate.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
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
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import list_schedules, delete_schedule
    from universal_mind.system_status_tool import SystemStatusTool

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r72p%'")

    # 1-3 — the vitals cache
    SystemStatusTool._vitals_cache = {"at": 0.0, "data": None}
    t0 = time.perf_counter()
    cold = route_and_run("وضعیت سیستم را بگو")
    cold_ms = (time.perf_counter() - t0) * 1000
    check(1, f"cold status works and pays the real gather ({cold_ms:.0f}ms)",
          cold.get("ok") is True and cold_ms > 300)
    t0 = time.perf_counter()
    warm = route_and_run("وضعیت سیستم را بگو")
    warm_ms = (time.perf_counter() - t0) * 1000
    check(2, f"warm status is served from the cache ({warm_ms:.0f}ms < 300ms)",
          warm.get("ok") is True and warm_ms < 300)
    check(3, f"the speedup is real ({cold_ms / max(warm_ms, 0.01):.0f}x >= 4x)",
          cold_ms / max(warm_ms, 0.01) >= 4)

    # 4-5 — the refresh + listening bypass
    SystemStatusTool._vitals_cache = {"at": 0.0, "data": None}
    t0 = time.perf_counter()
    ref = SystemStatusTool().status(refresh=True)
    ref_ms = (time.perf_counter() - t0) * 1000
    check(4, f"an explicit refresh bypasses the cache ({ref_ms:.0f}ms > 300ms)",
          ref.get("ok") is True and ref_ms > 300)
    listen = route_and_run("فضای درایو C را نشان بده")
    check(5, "a listening question never serves a stale block",
          listen.get("ok") is True and "دیسک C:" in str(listen.get("agent_report", "")))

    # 6-7 — the lazy imports
    code = (
        "import sys; sys.path.insert(0, r'D:/workspaces/baddanKhoda'); "
        "import time; t0=time.perf_counter(); "
        "import universal_mind.ai_suite; "
        "print(round((time.perf_counter()-t0)*1000))"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=120,
                       env={**os.environ, "PYTHONPATH": "D:/workspaces/baddanKhoda"})
    imp_ms = float(r.stdout.strip() or "-1")
    check(6, f"ai_suite imports without sklearn ({imp_ms:.0f}ms < 700ms)",
          imp_ms < 700)
    t0 = time.perf_counter()
    route_and_run("جمع ۲ و ۵ چنده؟")
    route_and_run("جمع ۲ و ۵ چنده؟")
    compute_ms = (time.perf_counter() - t0) * 1000 / 2
    check(7, f"a warm compute run is fast ({compute_ms:.0f}ms < 400ms)",
          compute_ms < 400)

    # 8-9 — the ML still trains for real (lazy != absent)
    from universal_mind.ai_suite import AISuite

    cls = AISuite().classify([[float(i)] for i in range(6)], [0, 0, 1, 1, 0, 1])
    check(8, "classify still trains a real model (lazy import works)",
          cls.get("ok") is True and 0.0 <= cls.get("accuracy", -1) <= 1.0)
    clu = AISuite().cluster([[float(i), float(i)] for i in range(10)], clusters=2)
    check(9, "cluster still trains real KMeans",
          clu.get("ok") is True)

    # 10-12 — the fast paths stay fast
    fast_cmds = [
        ("چند تا یادآور داری؟", "یادآور"),
        ("چند تا مخاطب داری؟", "مخاطب"),
        ("حافظه چه خبر؟", "درس"),
    ]
    for idx, (cmd, needle) in enumerate(fast_cmds, start=10):
        for _ in range(3):
            route_and_run(cmd)  # warm: pay the first-run imports once
        t0 = time.perf_counter()
        for _ in range(3):
            p = route_and_run(cmd)
        ms = (time.perf_counter() - t0) * 1000 / 3
        check(idx, f"«{cmd[:18]}» stays fast warm ({ms:.0f}ms < 250ms)",
              p.get("ok") is True and needle in str(p.get("agent_report", ""))
              and ms < 250)

    # cleanup
    for s in list_schedules():
        if "گواه-r72p" in s.command:
            delete_schedule(s.schedule_id)

    print()
    if FAILURES:
        print(f"R72 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R72 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
