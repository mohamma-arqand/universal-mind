#!/usr/bin/env python3
"""Probe: R39 — the empty band (warm hand-off), the unknown band (real
suggestions), the English near-miss (chart → نمودار), and the 14x hot-path
(the persistent file validated once per process). All live in the gate."""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R39 recovery + hot path:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import tempfile
    import time
    from contextlib import ExitStack
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    # R42 — the whole probe rides an ISOLATED store: a probe must never
    # litter the operator's history (the L3c singleton check runs AFTER
    # the stack closes, back on the live class).
    _iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r39.db"))
    with ExitStack() as _stack:
        _stack.enter_context(
            mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: _iso))
        )

        # L1 — the empty band: warm hand-off, never a silent hole.
        empty = route_and_run("")
        _ok("empty band hand-off",
            bool(empty.get("agent_report")) and "ننوشتی" in empty["agent_report"])

        # L2 — the unknown band carries REAL capability suggestions.
        unknown = route_and_run("سنجاق کن نقشه را")
        sugg = unknown.get("suggestions") or []
        _ok("unknown band suggests", bool(sugg) and all(len(s) >= 3 for s in sugg),
            f"sugg={sugg}")
        _ok("unknown report names them", "شاید" in str(unknown.get("agent_report")))

        # L2b — the English near-miss still points home.
        en = route_and_run("draw a chart of 1 and 5")
        _ok("english near-miss", "نمودار" in (en.get("suggestions") or []))

        # L3 — the hot path: 10 simple runs well under a second each.
        route_and_run("میانگین ۵ و ۷ را حساب کن")  # warm
        t0 = time.perf_counter()
        for _ in range(10):
            route_and_run("میانگین ۵ و ۷ را حساب کن")
        per = (time.perf_counter() - t0) / 10
        _ok("hot path < 150ms/run", per < 0.15, f"{per * 1000:.0f}ms/run")

    # L3b — corruption at an explicit path still fails loudly.
    d = Path(tempfile.mkdtemp()) / "corrupt.db"
    d.write_bytes(b"NOT-SQLITE-HEADER!" + b"\x00" * 48)
    try:
        DatabaseSuite(str(d))
        _ok("corrupt explicit path caught", False)
    except RuntimeError:
        _ok("corrupt explicit path caught", True)

    # L3c — the shared suite is one wrapper, reads what it writes.
    a = DatabaseSuite.shared_persistent()
    b = DatabaseSuite.shared_persistent()
    _ok("shared persistent singleton", a is b)

    sys.stderr.write("R39 recovery + hot path: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())