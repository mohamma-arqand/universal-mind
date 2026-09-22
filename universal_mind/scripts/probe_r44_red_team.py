#!/usr/bin/env python3
"""Probe: R44 item 6 — the nightly red team.

Live laws:
1. The REAL router survives the whole hostile corpus honestly — every
   answer graded, the sweep count printed, never assumed.
2. A sabotaged line (an injected crash) IS caught: a finding row + a
   self-repair goal — the platform files its own weakness as work.
3. The healthy sweep files nothing (no false findings on an honest platform).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-6 (the nightly red team):\n")


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

    # H1 — the honest sweep over the real router.
    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-rt.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.red_team import HOSTILE_CORPUS, run_red_team

        out = run_red_team(store=iso)
        _ok("corpus is fixed", len(HOSTILE_CORPUS) >= 8, f"lines={len(HOSTILE_CORPUS)}")
        _ok("every line graded", out["total"] == out["honest"] + len(out["findings"]),
            f"honest={out['honest']}, findings={len(out['findings'])}")
        _ok("a healthy platform files nothing", out["findings"] == [])

        # H2 — sabotage: one line crashes; the sweep MUST catch it.
        import universal_mind.persian_router as pr

        from typing import Any as _Any

        real = pr.route_and_run

        def _sabotage(cmd: str, *_a: _Any, **_kw: _Any) -> dict[str, _Any]:
            if "میانگین هیچی" in cmd:
                raise RuntimeError("saboteur")
            return real(cmd)

        iso2 = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-rt2.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                               classmethod(lambda cls: iso2)):
            with mock_patch.object(pr, "route_and_run", side_effect=_sabotage):
                out2 = run_red_team(store=iso2)
            _ok("the injected crash is caught",
                any(f["kind"] == "crash" for f in out2["findings"]),
                f"findings={len(out2['findings'])}")
            rows = iso2.query("SELECT goal FROM goals")["rows"]
            _ok("the weakness becomes a self-repair goal",
                bool(rows) and "red-team" in str(rows[0]["goal"]))

    sys.stderr.write("R44-6: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
