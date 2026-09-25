#!/usr/bin/env python3
"""Probe: R44 item 14 — the drift detector fires on real rot.

Two drifts, measured not assumed:
1. PERFORMANCE — the hot path vs the committed ``perf_baseline.json`` as a
   RATIO (machine-independent); >= 2x is red. An artificial drift (a planted
   tiny baseline) must go red — a detector that never fires is decoration.
2. REPORT LAWS — the golden corpus through the live router: every vanished
   promise and every new leak is named, and a crash is drift, never a skip.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import patch as mock_patch

sys.path.insert(0, "..")

sys.stderr.write("PROBE R44-14 (the drift detector):\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    import universal_mind.drift as drift

    # H1 — the real baseline exists and the current build is not drifting.
    base = drift.load_baseline()
    _ok("a committed baseline exists", base is not None and float(base["hot_path_ms"]) > 0,
        f"{(base or {}).get('hot_path_ms')}ms")
    live = drift.check_perf_drift()
    _ok("the current build passes its own perf gate", live.ok, live.detail)

    # H2 — the gate really FIRES: an artificial drift goes red.
    with mock_patch.object(drift, "load_baseline", lambda: {"hot_path_ms": 5.0}):
        fake = drift.check_perf_drift()
    _ok("an artificial 10x+ slowdown goes red", fake.ok is False, fake.detail)

    # H3 — no baseline = honest refusal, never a silent pass.
    with mock_patch.object(drift, "load_baseline", lambda: None):
        bare = drift.check_perf_drift()
    _ok("no baseline is an honest refusal", bare.ok is False and "خط مبنا" in bare.detail)

    # H4 — the golden report corpus is green on the live router.
    verdicts: Any = drift.check_report_drift()
    _ok("the report corpus is green", bool(verdicts) and all(v.ok for v in verdicts),
        f"{len(verdicts)} laws")

    # H5 — a planted leak is caught by name (the detector is not vacuous).
    leak_corpus = [("خدانگهدار", {"must_contain": [], "must_not_contain": ["منتظر"]})]
    with mock_patch.object(drift, "GOLDEN_REPORT_CORPUS", leak_corpus):
        planted = drift.check_report_drift()
    _ok("a planted report leak is caught", planted[0].ok is False, planted[0].detail[:60])

    sys.stderr.write("R44-14: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
