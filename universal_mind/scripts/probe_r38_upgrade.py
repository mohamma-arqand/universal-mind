#!/usr/bin/env python3
"""Probe: R38 — report-in-payload, the reader-speak flows, the conversation's
anaphora, and the vague goal step that inherits its subject. All cross-checked
live in the release gate.

Exit non-zero unless every hold is green.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "..")

sys.stderr.write("PROBE R38 upgrader map:\n")


def _ok(name: str, cond: bool, extra: str = "") -> None:
    mark = "PASS" if cond else "FAIL"
    sys.stderr.write(f"  [{mark}] {name}" + (f" — {extra}" if extra else "") + "\n")
    if not cond:
        raise SystemExit(1)


def main() -> int:
    from universal_mind.persian_router import route_and_run
    from universal_mind.orchestration import _flow_params

    # L1 — the fluent report rides in the payload (CLI/API/chat one source).
    r = route_and_run("میانگین ۵ و ۷ را حساب کن")
    _ok("L1 report rides in payload", bool(r.get("ok")) and bool(r.get("agent_report")),
        f"route={r.get('route')}")

    # L2 — web/pdf/ocr readers speak and become reports.
    _ok("L2 webfetch speaks",
        (_flow_params("speech", {}, "webfetch", {"preview": "متن", "title": "ت"},
                      "بخوان و بلند بخوان", ()).__getitem__(1)) is not None)
    reports = all(
        (_flow_params("pdf", {}, p, {"text": "متن"}, "فرمان", ())[1] is not None)
        for p in ("webfetch", "pdfreader", "ocr")
    )
    reports = bool(reports)
    _ok("L2 readers become reports", reports)

    # L3/L4 — the conversation-memory probes ride an ISOLATED context store
    # too: probes run back-to-back in the gate and the LIVE last_context left
    # by an earlier probe must not decide this probe's answer (caught live:
    # 'vague action inherits' failed because r37 had left a stale subject).
    import tempfile
    from pathlib import Path
    from unittest.mock import patch as mock_patch

    from universal_mind.database_suite import DatabaseSuite

    _suite = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "probe-r38.db"))
    with mock_patch(
        "universal_mind.database_suite.DatabaseSuite.shared_persistent",
        classmethod(lambda cls: _suite),
    ):
        # L3 — the conversation's anaphora resolves to the last run.
        route_and_run("میانگین ۱ و ۲ را حساب کن")
        anaphora = route_and_run("و همان را دوباره بکن")
        own = route_and_run("و حالا نمودارش را بکش")
    _ok("L3 anaphora reuses prior", bool(anaphora.get("ok")) and "همان" in str(anaphora.get("agent_report", "")),
        f"route={anaphora.get('route')}")
    _ok("L3 own-capability marks subject",
        own.get("route") == ["chart"] and own["result"].get("anaphora_of"))

    # L4 — a vague goal step inherits the prior subject. The goal store is
    # ISOLATED (same _suite): the probe runs on every release and must never
    # litter the durable DB (caught live: 21 duplicate rows across runs).
    with mock_patch(
        "universal_mind.database_suite.DatabaseSuite.shared_persistent",
        classmethod(lambda cls: _suite),
    ):
        vague = route_and_run("حالا تحلیلش کن")
    _ok("L4 vague action inherits", bool(vague.get("ok")) and "همان" in str(vague.get("agent_report", "")),
        f"route={vague.get('route')}")
    with mock_patch(
        "universal_mind.database_suite.DatabaseSuite.shared_persistent",
        classmethod(lambda cls: _suite),
    ):
        from universal_mind.agent_loop import run_goal, start_goal

        s = start_goal("هدف: ضمیر زنده", ("نمودار ۱ و ۵ را بکش", "حالا تحلیلش کن", "گزارشش را بساز"))
        g = run_goal(s["goal_id"])
    _ok("L4 vague goal step completes", g.finished and all(x.ok for x in g.steps))

    sys.stderr.write("R38 upgrade map: ALL HOLDS GREEN\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())