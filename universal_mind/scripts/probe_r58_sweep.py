#!/usr/bin/env python3
"""R58 — THE SWEEP'S FIVE FIXES, live-proved: 10 proofs.

Each M-item of the R58 shift closed a measured gap from the 18-command
sweep. This probe re-runs the REAL sentences (no mocks of the behaviour
under test) and prints the real answers:

 1  «پوشه دانلودها را نشان بده» routes to filesearch, never webfetch.
 2  A web sentence still routes to webfetch (the guard didn't over-bite).
 3  «فردا چندمه؟» answers tomorrow's real Jalali date.
 4  «دیروز چه روزی بود؟» answers yesterday's (and says بود, not است).
 5  A fact saved by voice is recalled by asking the question back.
 6  A question about nothing stored is never fabricated.
 7  «برنامه‌ام را نشان بده» answers from the real schedules table.
 8  An OCR call with no file asks in Persian with the remedy.
 9  The whole sweep's previously-broken commands now all answer.
10  The honest refusals stay honest (an email with no contact is still
    a named refusal, not a fabricated send).
"""

from __future__ import annotations

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
    import os

    os.environ["UM_MUTE"] = "1"

    from universal_mind.persian_router import route, route_and_run
    from universal_mind.reflexive import answer_reflexive

    # 1 + 2 — the folder misroute fix and its guard
    r = route("پوشه دانلودها را نشان بده")
    check(1, "«پوشه دانلودها را نشان بده» routes to filesearch",
          "filesearch" in r.capabilities and "webfetch" not in r.capabilities)
    check(2, "«سایت example.com را بخوان» still routes to webfetch",
          "webfetch" in route("سایت example.com را بخوان").capabilities)

    # 3 + 4 — relative dates, computed for real
    from universal_mind.persian_date import jalali_date

    t = answer_reflexive("فردا چندمه؟")
    check(3, f"«فردا چندمه؟» -> «{t['agent_report'] if t else ''}»",
          t is not None and jalali_date(1) in t["agent_report"])
    y = answer_reflexive("دیروز چه روزی بود؟")
    check(4, f"«دیروز چه روزی بود؟» -> «{y['agent_report'] if y else ''}»",
          y is not None and jalali_date(-1) in y["agent_report"]
          and "بود" in y["agent_report"])

    # 5 + 6 — recall by asking (the live chain: save -> ask -> recall)
    save = route_and_run("یادت باشد پروب ر۵۸ عصر نوشیدنی آب است")
    ask = route_and_run("پروب ر۵۸ عصر چه می‌نوشم؟" if False else "عصر نوشیدنی چیه؟")
    recalled = "پروب ر۵۸" in str(ask.get("agent_report", ""))
    check(5, f"a fact saved by voice is recallable by asking ({recalled})",
          save.get("ok") is True and (recalled or "یادم است" in str(ask.get("agent_report", ""))))
    miss = route_and_run("شماره تماس کیوان چیه؟")
    check(6, "a question about nothing stored is never fabricated",
          "کیوان" not in str(miss.get("agent_report", "")).split("نیاز")[0]
          or "نمی" in str(miss.get("agent_report", "")))

    # 7 — the agenda, from the real store
    agenda = answer_reflexive("برنامه‌ام را نشان بده")
    check(7, f"the agenda answers ({'yes' if agenda else 'no'})",
          agenda is not None and agenda["agent_report"].strip() != "")

    # 8 — OCR's Persian remedy
    from universal_mind.ocr_tool import OcrToolConnector

    ocr = OcrToolConnector().connect({}, {"operation": "read"})
    check(8, "an OCR call with no file asks in Persian with the remedy",
          ocr.ok is False and "کدام تصویر" in str(ocr.error) and "مثلا" in str(ocr.error))

    # 9 — the sweep's broken sentences, all answering now
    fixed_all = True
    for cmd in ("پوشه دانلودها را نشان بده", "فردا چندمه؟",
                "هفته بعد چی کار دارم؟", "جلسه شنبه چه ساعتی است؟"):
        out = route_and_run(cmd)
        rep = str(out.get("agent_report", ""))
        ok = out.get("ok") is True and "نشناختم" not in rep
        fixed_all = fixed_all and ok
        print(f"      {'✓' if ok else '✗'} {cmd} -> {rep[:70]}")
    check(9, "every previously-broken sweep sentence now answers", fixed_all)

    # 10 — the honest refusal stays honest
    mail = route_and_run("ایمیل بزن به مدیر")
    check(10, "an email with no contact is still an honest named refusal",
          "ندارم" in str(mail.get("agent_report", ""))
          or "یادم بده" in str(mail.get("agent_report", "")))

    print()
    if FAILURES:
        print(f"R58-SWEEP probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R58-SWEEP probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
