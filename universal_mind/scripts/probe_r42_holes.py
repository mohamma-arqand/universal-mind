#!/usr/bin/env python3
"""Probe: R42 — the operator's store is sacred, the navigation holes closed.

Two live laws, both caught by real measurement:
1. A full verify run must add ZERO rows to the operator's run_history —
   probes and tests ride isolated stores (R41 fixed the goal store; R42
   closes the history store, where the sweep found 8,106 rows/day leaking).
2. The everyday-command sweep answers every hole it found: «چی بلدی؟»،
   «امروز چی کار کردی؟»، «حافظهات چی میگن؟»، «خدانگهدار» — no «نشناختم».
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R42 holes + store isolation:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    from universal_mind.database_suite import DatabaseSuite

    # H1 — the live store does not grow while a routed run executes on an
    # isolated store (the exact leak this round closed).
    live = DatabaseSuite(persistent=True)
    before = live.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]

    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r42.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        # H2 — the sweep holes answer, none say «نشناختم».
        holes = (
            "چی بلدی؟",
            "قابلیتهات رو نشون بده",
            "کمک کن چی کار کنم؟",
            "امروز چی کار کردی؟",
            "فایلهای ساختهشده امروز",
            "حافظهات چی میگن؟",
            "چی یاد گرفتی؟",
            "خدانگهدار",
        )
        answered = 0
        for cmd in holes:
            p = route_and_run(cmd)
            rep = str(p.get("agent_report") or "")
            if rep and "نشناختم" not in rep:
                answered += 1
            else:
                _ok(f"hole answered: {cmd}", False, rep[:50])
        _ok("all 8 sweep holes answered", answered == len(holes),
            f"{answered}/{len(holes)}")

        # a real run lands in the ISOLATED store only
        route_and_run("میانگین ۵ و ۷ را حساب کن")

    after = live.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
    _ok("live store untouched by isolated runs", after == before,
        f"before={before} after={after}")

    # H3 — the isolated store DID record the run (isolation is not a no-op).
    # R46 re-pin: the sweep's reflexive reads NEVER record (speech answers
    # are not runs) — exactly ONE row lands, from the real command.
    iso_n = iso.query("SELECT COUNT(*) AS n FROM run_history")["rows"][0]["n"]
    _ok("isolated store recorded the run", iso_n == 1,
        f"rows={iso_n}")  # the sweep's reflexive reads don't record; the run does

    sys.stderr.write("R42 holes + isolation: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
