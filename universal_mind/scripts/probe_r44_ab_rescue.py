#!/usr/bin/env python3
"""Probe: R44 items 7+8 — the parameter A/B, the rescue chain.

Live laws:
1. The ambiguous kind runs a REAL contest in the production chain: the
   ruling rides the shipped payload and the Persian report announces it.
2. A NAMED kind never contests (the operator's word wins — no theater).
3. The rescue path: a failed step's best learned alternative; the pair
   lands in planner_lessons (the failure teaches nothing, the rescue does).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-7/8 (the parameter A/B + the rescue chain):\n")


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

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-ab.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        # H1 — the real contest: ambiguous kind → the ruling in the report.
        p = route_and_run("نمودار از ۲ و ۵ و ۹ کن")
        _ok("the contest ran in the real chain", p.get("ok") is True and "مسابقهی A/B" in str(p.get("ab_ruling")),
            str(p.get("ab_ruling"))[:50])
        _ok("the report announces the ruling", "مسابقهی A/B" in str(p.get("agent_report") or ""))

        # H2 — a NAMED kind never contests.
        p2 = route_and_run("نمودار میلهای بساز")
        _ok("a named kind never contests", p2.get("ab_ruling") is None)

    # H3 — the rescue chain: the pair lands in lessons (isolated store).
    import universal_mind.planner_learning as pl

    iso2 = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-ab2.db"))
    with mock_patch.object(pl, "_store", lambda: iso2):
        pl.teach("webfetch", "fetch", 0.0, False)  # the failure teaches nothing
        pl.teach("database", "query", 0.95, True)  # the rescue teaches
        best = pl.best_learned_operation("database")
        _ok("the rescue is learned", best is not None and best.operation == "query",
            f"best={best.operation if best else None}")
        lessons = pl.learned_operations("webfetch")
        _ok("the failure teaches nothing", all(l.operation != "fetch" or False for l in lessons),
            f"webfetch lessons={len(lessons)}")

    sys.stderr.write("R44-7/8: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
