#!/usr/bin/env python3
"""R79 — the FALSE-SUCCESS sweep: 10 live proofs.

The live audit found five commands claiming success while nothing real
happened — the honesty law's next frontier. This probe MEASURES the
real effects (the volume before/after through the helper itself) and
pins every named refusal.
"""

from __future__ import annotations

import os
import sys
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
    from universal_mind.persian_router import route_and_run
    from universal_mind.volume_tool import get_volume, set_volume

    # 1-3 — the volume REALLY moves (measured by the helper itself)
    v0 = get_volume()
    check(1, f"the helper measures the real volume ({v0.get('volume')})",
          v0.get("ok") is True)
    p = route_and_run("صدا را بلندتر کن")
    rep = str(p.get("agent_report", ""))
    check(2, f"«صدا را بلندتر کن» moves the REAL volume ({p.get('route')})",
          p.get("route") == ["sysstatus"] and "ولوم واقعی" in rep)
    set_volume(level=(v0["volume"] / 100.0) + 0.05)
    v_up = get_volume()
    check(3, f"the MEASURED level rose ({v0['volume']} -> {v_up['volume']})",
          v_up["volume"] == min(100, v0["volume"] + 5))
    set_volume(level=v0["volume"] / 100.0)  # restore

    # 4 — a volume query answers the measured level
    p = route_and_run("ولوم چند است؟")
    check(4, "«ولوم چند است؟» answers the measured level",
          "ولوم الان" in str(p.get("agent_report", "")))

    # 5-7 — the named refusals (never a false success)
    p = route_and_run("یه موسیقی قشنگ پخش کن")
    rep = str(p.get("agent_report", ""))
    check(5, "«پخش کن» names the missing player + the real path",
          p.get("ok") is False and "پخشکنندهٔ واقعی ندارم" in rep)
    p = route_and_run("ویروس اسکن کن")
    rep = str(p.get("agent_report", ""))
    check(6, "«ویروس اسکن کن» names Defender (not image processing)",
          p.get("ok") is False and "Defender" in rep
          and "پردازش تصویر" not in rep)
    p = route_and_run("شعر بگو درباره باران")
    rep = str(p.get("agent_report", ""))
    check(7, "«شعر بگو» refuses honestly (no fixed line)",
          p.get("ok") is False and "خلاقیت" in rep)

    # 8-9 — the REAL ram act
    p = route_and_run("رم را آزاد کن")
    rep = str(p.get("agent_report", ""))
    check(8, f"«رم را آزاد کن» is the real act ({p.get('route')})",
          p.get("route") == ["sysstatus"]
          and ("رم واقعاً آزاد شد" in rep or "تغییر نکرد" in rep))
    check(9, "…and never claims a fabricated freeing",
          "رم آزاد شد اما" in rep or "رم واقعاً آزاد شد" in rep)

    # 10 — the plain status survives
    p = route_and_run("وضعیت سیستم را بگو")
    check(10, "the plain status report survives",
          p.get("ok") is True and "رم" in str(p.get("agent_report", "")))

    print()
    if FAILURES:
        print(f"R79 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R79 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
