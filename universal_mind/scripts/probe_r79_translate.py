#!/usr/bin/env python3
"""R79 B3 — the TRANSLATE wave: 8 live proofs.

«ترجمه» was webfetch's word (site reading!) and the greeting gate ate
«سلام رو به انگلیسی ترجمه کن». Translate is now a real offline
capability with a shipped pocket dictionary, script-decided direction,
and named refusal for unknown words.
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

    # 1 — translation is work, not a greeting
    p = route_and_run("سلام رو به انگلیسی ترجمه کن")
    check(1, f"«سلام … ترجمه کن» is translate ({p.get('route')})",
          p.get("route") == ["translate"] and "hello" in
          str(p.get("agent_report", "")))

    # 2 — fa → en
    p = route_and_run("«کتاب» را به انگلیسی ترجمه کن")
    check(2, "«کتاب» -> book", "book" in str(p.get("agent_report", "")))

    # 3 — en → fa
    p = route_and_run("water را به فارسی ترجمه کن")
    check(3, "water -> آب", "آب" in str(p.get("agent_report", "")))

    # 4 — the SCRIPT decides the direction
    p = route_and_run("«برنامه» را به فارسی ترجمه کن")
    check(4, "Persian word + «به فارسی» still -> English",
          "program" in str(p.get("agent_report", "")))

    # 5 — unknown word = named refusal, never a guess
    p = route_and_run("«زلمزلمزو» را به انگلیسی ترجمه کن")
    rep = str(p.get("agent_report", ""))
    check(5, "unknown word is a NAMED refusal",
          p.get("ok") is False and "واژهنامه" in rep and "نمیسازم" in rep)

    # 6 — the greeting itself survives
    p = route_and_run("سلام")
    check(6, f"plain «سلام» stays conversational ({p.get('route')})",
          p.get("route") == ["conversational"])

    # 7 — the dictionary is real shipped data
    import json

    d = json.loads((Path(__file__).resolve().parents[1] / "data" /
                    "dict_fa_en.json").read_text(encoding="utf-8"))
    check(7, f"the pocket dictionary is real ({len(d['fa2en'])}+ entries)",
          d["fa2en"]["سلام"] == "hello" and len(d["fa2en"]) >= 100)

    # 8 — neighbours: webfetch still reads sites
    p = route_and_run("سایت example.com را بخوان")
    check(8, "webfetch still owns site reading",
          "webfetch" in (p.get("route") or []))

    print()
    if FAILURES:
        print(f"R79-B3 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R79-B3 probe: ALL 8 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
