#!/usr/bin/env python3
"""R65 — the identity/recurring/contact/date sweep's fixes, live: 12 proofs.

The 18-command sweep measured 8 classes (two of them LIVE LIES - an
immediate speech instead of a schedule; a registration instead of a
filtered list); P1-P8 closed them. This probe re-runs the REAL
sentences:

 1  «اسمم چیه؟» answers from the operator's own memory (or teaches it).
 2  The stored name is really in named_memory.
 3  «هر ۳۰ دقیقه … بگو» registers a RECURRING schedule (nothing speaks).
 4  The stored recurring action carries the operator's words (no filler).
 5  «یادآورهای فردا» lists a FILTER, not a registration.
 6  «پس‌فردا» filters its own day (not the «فردا» substring).
 7  «مخاطبهام را نشان بده» lists the real book.
 8  «امروز چندشنبه است؟» matches the independent weekday computation.
 9  «جذر ۱۶ چنده؟» answers from data alone (ok=True, «نتیجه ۴»).
10  «دانلودها را نشان بده» searches the REAL Downloads folder.
11  «فایل X را به Y جابجا کن» moves for real (source gone).
12  An existing destination refuses the move without confirmation.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM named_memory WHERE fact LIKE '%اسم من گواه-r65%'")
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r65%'")
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r65%'")

    # 1-2 — the personal memory
    report("یادت باشد اسم من گواه-r65 است")
    r1 = report("اسمم چیه؟")
    check(1, "the name question answers from the operator's own memory",
          "گواه-r65" in r1 and "مدل زبانی" not in r1)
    q2 = db.query("SELECT COUNT(*) n FROM named_memory WHERE fact LIKE '%گواه-r65%'")
    check(2, "the name is really stored in named_memory",
          int(q2["rows"][0]["n"]) == 1)

    # 3-4 — the recurring speech
    r3 = report("هر ۳۰ دقیقه یکبار بهم بگو گواه-r65 را یادم بیار")
    q3 = db.query("SELECT command, every_minutes FROM schedules WHERE command LIKE '%گواه-r65%'")
    rows3 = q3.get("rows", []) if q3.get("ok") else []
    check(3, "a recurring-interval sentence registers a schedule",
          rows3 and int(rows3[0]["every_minutes"]) == 30
          and "تکراری ثبت شد" in r3)
    check(4, "the stored action is the operator's words (no «یکبار» filler)",
          rows3 and rows3[0]["command"].startswith("بهم بگو"))

    # 5-6 — the filtered list
    report("یادم باشه فردا ساعت ۷ گواه-r65 را بدهکار کن")
    report("یادم باشه پس‌فردا ساعت ۵ گواه-r65 بعدی")
    n_before = _count(db, "گواه-r65")
    r5 = report("یادآورهای فردا را نشان بده")
    n_after = _count(db, "گواه-r65")
    check(5, "the filtered list registers nothing",
          n_before == n_after and "(فردا)" in r5 and "بدهکار" in r5)
    r6 = report("یادآورهای پس‌فردا را نشان بده")
    check(6, "«پس‌فردا» filters its own day (substring law)",
          "(پس‌فردا)" in r6 and "بعدی" in r6 and "بدهکار" not in r6)

    # 7 — the contact book
    from universal_mind.contacts import save

    save("گواه-r65", "w65@example.com")
    r7 = report("مخاطبهام را نشان بده")
    check(7, "the contact book lists the real names",
          "گواه-r65" in r7 and "w65@example.com" in r7)

    # 8 — the weekday
    r8 = report("امروز چندشنبه است؟")
    _DAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
    exp_today = _DAYS[(datetime.now().weekday() + 2) % 7]
    check(8, "the weekday matches the independent computation",
          f"امروز {exp_today} است" in r8)

    # 9 — the scalar intent
    p9 = route_and_run("جذر ۱۶ چنده؟")
    check(9, "sqrt answers from data alone (compute aside)",
          p9.get("ok") is True and p9.get("route") == ["data"]
          and "نتیجه ۴" in str(p9.get("agent_report", "")))

    # 10 — the real Downloads
    p10 = route_and_run("دانلودها را نشان بده")
    check(10, "the spoken folder searches the REAL Downloads",
          p10.get("route") == ["filesearch"]
          and str(Path.home() / "Downloads") in str(p10.get("agent_report", "")))

    # 11-12 — the move
    src = Path("D:/um_r65_probe_a.txt")
    dst = Path("D:/um_r65_probe_b.txt")
    src.write_text("محتوای گواه", encoding="utf-8")
    p11 = route_and_run(f"فایل {src} را به {dst} جابجا کن")
    moved = dst.exists() and not src.exists() and dst.read_text(encoding="utf-8") == "محتوای گواه"
    check(11, "the move is real (source gone, destination exact)",
          p11.get("ok") is True and moved)
    src.write_text("دوباره", encoding="utf-8")
    p12 = route_and_run(f"فایل {src} را به {dst} جابجا کن")
    check(12, "an existing destination refuses without confirmation",
          p12.get("ok") is False and src.exists() and dst.exists())
    src.unlink(missing_ok=True)
    dst.unlink(missing_ok=True)

    # cleanup
    db.execute("DELETE FROM named_memory WHERE fact LIKE '%اسم من گواه-r65%'")
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r65%'")
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r65%'")

    print()
    if FAILURES:
        print(f"R65 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R65 probe: ALL 12 LIVE PROOFS PASS")
    return 0


def _count(db: "DatabaseSuite", needle: str) -> int:
    q = db.query(f"SELECT COUNT(*) n FROM schedules WHERE command LIKE '%{needle}%'")
    return int(q["rows"][0]["n"]) if q.get("ok") else -1


if __name__ == "__main__":
    raise SystemExit(main())
