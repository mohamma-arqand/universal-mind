#!/usr/bin/env python3
"""R79 B5 — the KNOWLEDGE wave: 8 live proofs.

The offline factbook answers the everyday core before the honest
refusal — with sources; a miss keeps the refusal; math still computes.
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

    # 1-3 — facts answer with sources
    p = route_and_run("پایتخت فرانسه چیست؟")
    rep = str(p.get("agent_report", ""))
    check(1, f"«پایتخت فرانسه» answers from the factbook ({p.get('route')})",
          p.get("route") == ["knowledge"] and "پاریس" in rep and "منبع" in rep)
    p = route_and_run("ایران چند استان دارد؟")
    check(2, "«چند استان» answers ۳۱ (was «نشناختم»)",
          p.get("ok") is True and "۳۱" in str(p.get("agent_report", "")))
    p = route_and_run("سرعت نور چند است؟")
    check(3, "«سرعت نور چند است» is knowledge, not compute",
          p.get("route") == ["knowledge"]
          and "۳۰۰" in str(p.get("agent_report", "")))

    # 4-5 — people and science
    p = route_and_run("مولانا کیست؟")
    check(4, "«مولانا کیست؟» answers with the biography",
          p.get("ok") is True and "مثنوی" in str(p.get("agent_report", "")))
    p = route_and_run("نورون چیست؟")
    check(5, "«نورون چیست؟» answers the science fact",
          p.get("ok") is True and "عصبی" in str(p.get("agent_report", "")))

    # 6 — a miss keeps the honest refusal (never a guess)
    p = route_and_run("کوارک فلان چیه؟")
    rep = str(p.get("agent_report", ""))
    check(6, "an unknown ask keeps the honest refusal",
          p.get("ok") is False and ("مدل زبانی" in rep or "حدس" in rep))

    # 7 — math still computes (no knowledge theft)
    p = route_and_run("۲۵ بعلاوه ۷ چند میشود؟")
    check(7, f"math still goes to compute ({p.get('route')})",
          "compute" in (p.get("route") or []))

    # 8 — the factbook is real data with sources
    import json

    d = json.loads((Path(__file__).resolve().parents[1] / "data" /
                    "facts_fa.json").read_text(encoding="utf-8"))
    check(8, f"the factbook ships clean ({len(d)} sourced facts)",
          len(d) >= 20 and all(f.get("source") for f in d))

    print()
    if FAILURES:
        print(f"R79-B5 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R79-B5 probe: ALL 8 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
