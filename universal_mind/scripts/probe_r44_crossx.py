#!/usr/bin/env python3
"""Probe: R44 item 5 — the cross-examiner (independent second numeric verdict).

Live laws:
1. The REAL chain carries the cross_exam: numpy vs pure-Python over the
   same series, status='agree' on a healthy run.
2. A disagreement is NAMED — the field and both values in the Persian voice.
3. The report speaks it: the operator SEES the second signature.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-5 (the cross-examiner):\n")


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

    iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r44-5.db"))
    with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
        from universal_mind.persian_router import route_and_run

        p = route_and_run("میانگین ۴ و ۶ و ۹ را حساب کن")
        exam = (p.get("result", {}).get("data") or {}).get("cross_exam")
        _ok("real chain cross-examines", isinstance(exam, dict) and exam.get("status") == "agree",
            f"status={exam.get('status') if isinstance(exam, dict) else None}")

        report = str(p.get("agent_report") or "")
        _ok("report speaks the second signature", "داور متقاطع عددی" in report)

        # the named disagreement — a sabotaged payload is caught, not silent
        from universal_mind.cross_examiner import cross_examine, persian_note

        bad = cross_examine({"mean": 7.0, "std": 2.0, "min": 4.0, "max": 9.0,
                             "median": 6.0, "count": 3, "_series": [4.0, 6.0, 9.0]})["cross_exam"]
        _ok("disagreement is a caught bug", bad.get("status") == "disagree" and bad.get("field") == "mean")
        note = persian_note(bad)
        _ok("the bug is NAMED in Persian", note is not None and "باگ" in note and "mean" in note)

    sys.stderr.write("R44-5: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
