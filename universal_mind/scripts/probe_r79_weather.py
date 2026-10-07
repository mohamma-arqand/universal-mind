#!/usr/bin/env python3
"""R79 B4 — the WEATHER wave: 8 live proofs.

The old answer refused «هوا چطوره؟» while the machine was online. The
weather is now the 33rd real capability: live open-meteo, a shipped
gazetteer, a cache that NAMES its age, and a refusal that never guesses.
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

    # 1-2 — live answers with real numbers
    p = route_and_run("هوای تهران چطوره؟")
    rep = str(p.get("agent_report", ""))
    check(1, f"«هوای تهران چطوره؟» is the weather route ({p.get('route')})",
          p.get("route") == ["weather"] and "درجه" in rep)
    check(2, "…and the source is labelled (live or cache)",
          ("زنده" in rep) or ("کش" in rep))

    # 3-4 — the gazetteer and the default
    p = route_and_run("هوای شیراز چطوره؟")
    check(3, "«شیراز» resolves from the shipped gazetteer",
          p.get("ok") is True and "شیراز" in str(p.get("agent_report", "")))
    p = route_and_run("هوا الان چطوره؟")
    check(4, "no-city ask defaults to Tehran (الان is not a city)",
          p.get("ok") is True and "تهران" in str(p.get("agent_report", "")))

    # 5 — unknown city = named refusal with the known list
    p = route_and_run("هوای زلمزو چطوره؟")
    rep = str(p.get("agent_report", ""))
    check(5, "an unknown city is a NAMED refusal",
          p.get("ok") is False and "زلمزو" in rep and "فهرست" in rep)

    # 6 — offline with a cached sample: the age is NAMED, never hidden
    import universal_mind.weather_tool as wt

    wt.weather("تهران")  # warm the cache (its liveness is check 1's business)
    real = wt.urllib.request.urlopen

    def _no_net(*_a, **_k):
        raise OSError("offline-proof")

    wt.urllib.request.urlopen = _no_net
    try:
        out = wt.weather("تهران")
        check(6, f"offline answers from cache and NAMES the age "
              f"({out.get('note', '')[:30]}…)",
              out.get("ok") is True and out.get("source") == "cache"
              and "دقیقه پیش" in str(out.get("note", "")))
    finally:
        wt.urllib.request.urlopen = real

    # 7 — offline with NO sample: the honest refusal, never a guess
    empty = wt._read_cache()
    saved = empty.get("یزد")
    empty.pop("یزد", None)
    wt._write_cache(empty)
    wt.urllib.request.urlopen = _no_net
    try:
        out2 = wt.weather("یزد")
        check(7, "offline with no sample is the honest refusal",
              out2.get("ok") is False and "حدس" in str(out2.get("error", "")))
    finally:
        wt.urllib.request.urlopen = real
        if saved:
            empty["یزد"] = saved
            wt._write_cache(empty)

    # 8 — the neighbour: system status untouched
    p = route_and_run("وضعیت سیستم را بگو")
    check(8, "the system-status neighbour survives",
          p.get("ok") is True and "رم" in str(p.get("agent_report", "")))

    print()
    if FAILURES:
        print(f"R79-B4 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R79-B4 probe: ALL 8 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
