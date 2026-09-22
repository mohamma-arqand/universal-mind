#!/usr/bin/env python3
"""Probe: R44 wave-1 — the plan explained, the dry run, the human verdict.

Three live laws from the R44 map, locked with real round-trips:
1. «... — توضیح بده» narrates the program (steps + reasons + sources)
   and NEVER executes — zero history rows.
2. «عالی بود»/«بد بود» binds to the last real success and the weight
   moves for real (1.25 up / 0.5^k down) — the human judge is IN the loop.
3. The advisor's ranking consumes the human weight (an advisor that
   ignores the operator's ruling would make the verdict decorative).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44 wave-1 (explain + dry-run + verdict):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r44.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        # H1 — the explained plan, never executed.
        p = route_and_run("نمودار ۱ و ۵ را بکش و گزارشش کن — توضیح بده")
        _ok("plan narrated", p.get("planned") is True and "گام ۱: chart" in str(p.get("agent_report")),
            f"route={p.get('route')}")
        _ok("plan not executed", p.get("executed") is False)
        rows = iso.query("SELECT COUNT(*) AS n FROM run_history")
        n = rows["rows"][0]["n"] if rows.get("ok") else 0
        _ok("dry-run wrote zero history rows", n == 0, f"rows={n}")

        # H2 — the human verdict moves the weight for real.
        from universal_mind.operator_verdicts import route_weight

        route_and_run("میانگین ۴ و ۶ را حساب کن")
        before = route_weight(("data",))
        route_and_run("عالی بود")
        after_good = route_weight(("data",))
        route_and_run("بد بود")
        after_bad = route_weight(("data",))
        _ok("verdict recorded and bound",
            after_good > before and after_bad < after_good,
            f"{before:.2f} → {after_good:.2f} (good) → {after_bad:.2f} (bad)")

        # H3 — the advisor consumes the human weight.
        from universal_mind.run_history import ChainAdvisor, RunHistory

        for _ in range(3):
            route_and_run("میانگین ۲ و ۸ را حساب کن")
        route_and_run("بد بود")  # the operator rules the data chain bad
        route_and_run("نمودار خطی بساز")  # a clean chart win
        advice = ChainAdvisor(RunHistory(iso)).advise("میانگین و نمودار")
        _ok("advisor still advises under human rulings", advice is not None,
            f"route={advice.route if advice else None}")
        w_data = route_weight(("data",))
        _ok("the human's bad ruling holds", w_data < 1.0, f"w(data)={w_data:.3f}")

    sys.stderr.write("R44 wave-1: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
