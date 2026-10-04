#!/usr/bin/env python3
"""R77 — the OPENER sweep: 10 live proofs.

«باز کن» fell to webfetch; files, folders, and the calculator all got
«کدام سایت؟». The opener opens the REAL thing on Windows and names it.
This probe ALSO verifies the effect on the live system: after an open,
the real process/window must exist (calc, notepad) — never a claimed
success with nothing there.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def _proc_alive(pattern: str) -> bool:
    """The live-process proof: Windows renames UWP apps (calc launches as
    CalculatorApp, not calc), so the check matches a PATTERN, never one
    exact name — the same lesson as the named lock."""
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        f"(Get-Process | Where-Object {{$_.ProcessName -match"
                        f" '{pattern}'}}).Count -gt 0"],
                       capture_output=True, text=True, timeout=15, check=False)
    return "True" in (r.stdout or "")


def main() -> int:
    os.environ["UM_MUTE"] = "1"
    from universal_mind.persian_router import route_and_run

    base = Path(r"D:/gwr77_probe")
    base.mkdir(exist_ok=True)
    f = base / "note.txt"
    f.write_text("probe R77\n", encoding="utf-8")
    sub = base / "subfolder"
    sub.mkdir(exist_ok=True)

    # 1-3 — the object classes route opener-only
    p = route_and_run(f"فایل {f} را باز کن")
    check(1, f"a FILE opens via opener ({p.get('route')})",
          p.get("route") == ["opener"] and p.get("ok") is True)
    p = route_and_run(f"پوشه {sub} را باز کن")
    check(2, f"a FOLDER opens via opener, textfile aside ({p.get('route')})",
          p.get("route") == ["opener"] and p.get("ok") is True)
    rep = str(p.get("agent_report", ""))
    check(3, "the report NAMES the thing opened",
          "باز شد" in rep and "subfolder" in rep)

    # 4-5 — the calculator: really opens (live process proof)
    p = route_and_run("ماشینحساب را باز کن")
    ok4 = p.get("ok") is True and p.get("route") == ["opener"]
    if ok4:
        time.sleep(1.5)
        ok4 = _proc_alive("Calculator")
    check(4, "«ماشینحساب» opens a REAL calculator process (live)", ok4)
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Get-Process | Where-Object {$_.ProcessName -match 'Calculator'}"
                    " | Stop-Process -Force"], timeout=15, check=False)

    # 6 — notepad with the file (verb + live process)
    p = route_and_run(f"فایل {f} را با notepad باز کن")
    ok6 = p.get("ok") is True
    if ok6:
        time.sleep(1.5)
        ok6 = _proc_alive("notepad")
    check(6, "«با notepad» really starts notepad (live)", ok6)
    subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                    "Get-Process -Name notepad -ErrorAction SilentlyContinue"
                    " | Stop-Process -Force"], timeout=15, check=False)

    # 7-8 — the honest refusals + the neighbours survive
    p = route_and_run(f"فایل {base / 'nope.txt'} را باز کن")
    check(7, "a missing path is a NAMED refusal",
          p.get("ok") is False and "نه مسیر موجود است" in str(p.get("agent_report", "")))
    p = route_and_run("سایت example.com را بخوان")
    check(8, f"reading a page keeps webfetch ({p.get('route')})",
          "webfetch" in (p.get("route") or []) and "opener" not in (p.get("route") or []))

    # 9-10 — the program table + the verb extraction
    from universal_mind.opener_tool import _PROGRAMS_FA

    check(9, "the Persian program table is real",
          _PROGRAMS_FA.get("ماشینحساب") == "calc"
          and _PROGRAMS_FA.get("تنظیمات ویندوز") == "ms-settings:")
    from universal_mind.persian_params import extract_params

    got = extract_params(f"فایل {f} را با notepad باز کن", "opener")
    check(10, f"the verb rides «با» ({got.get('verb')!r}) and the target rides the path",
          got.get("verb") == "notepad" and str(got.get("target", "")).endswith("note.txt"))

    print()
    if FAILURES:
        print(f"R77 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R77 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
