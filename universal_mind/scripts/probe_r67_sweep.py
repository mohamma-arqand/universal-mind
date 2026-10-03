#!/usr/bin/env python3
"""R67 — the status/file-ops/time sweep's fixes, live: 12 proofs.

The 15-command sweep measured 8 classes; P1-P8 closed them. This
probe re-runs the REAL sentences:

 1  «یادآوری N را غیرفعال کن» flips active and the row SURVIVES.
 2  «یادآوری N را فعال کن» re-arms it.
 3  «نام فایل X را عوض کن به Y» renames for real (both names named).
 4  An existing rename destination refuses without «روی همان فایل».
 5  «فایل X را به Y کپی کن» copies for real (the source survives).
 6  «حجم فایل X چقدر است؟» names the REAL size.
 7  «در پوشه X چند فایل هست؟» counts the real folder.
 8  «پوشه X را بساز» creates a real folder.
 9  «چند دقیقه تا ساعت ۲۰ مانده؟» matches the independent computation.
10  The contact bare-delete refuses and the row survives.
11  The confirmed contact delete removes the row.
12  An unknown contact name is an honest refusal.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from universal_mind.database_suite import DatabaseSuite  # noqa: E402

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    os.environ["UM_MUTE"] = "1"
    from universal_mind.contacts import save, list_contacts
    from universal_mind.persian_router import route_and_run
    from universal_mind.scheduler import delete_schedule, list_schedules, register

    def report(cmd: str) -> dict:
        return route_and_run(cmd)

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r67%'")
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r67%'")

    # 1-2 — the toggle
    register("هر روز ساعت ۷ گواه-r67 را بگو")
    sid = next(s.schedule_id for s in list_schedules() if "گواه-r67" in s.command)
    fa_sid = str(sid).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

    def active() -> bool:
        return next(s.active for s in list_schedules() if s.schedule_id == sid)

    p1 = report(f"یادآوری {fa_sid} را غیرفعال کن")
    check(1, "the toggle-off flips active and the row survives",
          p1.get("ok") is True and active() is False
          and any(s.schedule_id == sid for s in list_schedules()))
    p2 = report(f"یادآوری {fa_sid} را فعال کن")
    check(2, "the toggle-on re-arms it",
          p2.get("ok") is True and active() is True)
    delete_schedule(sid)

    # 3-4 — the rename
    a = Path("D:/um_r67_probe_a.txt")
    b = Path("D:/um_r67_probe_b.txt")
    a.write_text("محتوای گواه", encoding="utf-8")
    b.unlink(missing_ok=True)
    p3 = report(f"نام فایل {a} را عوض کن به {b}")
    check(3, "a real rename, both names in the answer",
          p3.get("ok") is True and not a.exists() and b.exists()
          and b.read_text(encoding="utf-8") == "محتوای گواه"
          and "نام عوض شد" in str(p3.get("agent_report", "")))
    a.write_text("دوباره", encoding="utf-8")
    p4 = report(f"نام فایل {a} را عوض کن به {b}")
    check(4, "an existing rename destination refuses without confirmation",
          p4.get("ok") is False and a.exists()
          and b.read_text(encoding="utf-8") == "محتوای گواه")
    a.unlink(missing_ok=True)
    b.unlink(missing_ok=True)

    # 5 — the copy
    a.write_text("محتوای گواه", encoding="utf-8")
    b.unlink(missing_ok=True)
    p5 = report(f"فایل {a} را به {b} کپی کن")
    check(5, "a real copy — the source survives",
          p5.get("ok") is True and a.exists()
          and b.read_text(encoding="utf-8") == "محتوای گواه"
          and "سر جایش است" in str(p5.get("agent_report", "")))

    # 6 — the size
    p6 = report(f"حجم فایل {a} چقدر است؟")
    n_bytes = len("محتوای گواه".encode("utf-8"))
    fa_bytes = str(n_bytes).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    check(6, "the real size is named",
          p6.get("ok") is True and f"{fa_bytes} بایت" in str(p6.get("agent_report", "")))

    # 7-8 — the folder ops
    import shutil

    fd = Path("D:/um_r67_probe_dir")
    shutil.rmtree(fd, ignore_errors=True)
    fd.mkdir()
    (fd / "f1.txt").write_text("x", encoding="utf-8")
    (fd / "sub").mkdir()
    p7 = report(f"در پوشه {fd} چند فایل هست؟")
    check(7, "the real folder count",
          p7.get("ok") is True and "۱ فایل" in str(p7.get("agent_report", ""))
          and "۱ پوشه" in str(p7.get("agent_report", "")))
    target = fd / "deep" / "gwr"
    p8 = report(f"پوشه {target} را بساز")
    check(8, "a real folder with parents",
          p8.get("ok") is True and target.is_dir())
    shutil.rmtree(fd, ignore_errors=True)
    a.unlink(missing_ok=True)
    b.unlink(missing_ok=True)

    # 9 — the named hour
    p9 = report("چند دقیقه تا ساعت ۲۰ مانده؟")
    now = datetime.now()
    tgt = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if tgt <= now:
        tgt += timedelta(days=1)
    mins = int((tgt - now).total_seconds() // 60)
    h, m = divmod(mins, 60)
    _fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    expect = (f"{h} ساعت و {m} دقیقه" if h else f"{mins} دقیقه").translate(_fa)
    check(9, "the named-hour distance matches the independent computation",
          p9.get("ok") is True and expect in str(p9.get("agent_report", "")))

    # 10-12 — the contact delete law
    save("گواه-r67", "r67@example.com")
    p10 = report("مخاطب گواه-r67 را حذف کن")
    check(10, "the bare contact-delete refuses and the row survives",
          p10.get("ok") is False and "تأیید" in str(p10.get("agent_report", ""))
          and any(r["name"] == "گواه-r67" for r in list_contacts()))
    p11 = report("مخاطب گواه-r67 را حذف کن — تأیید کن")
    check(11, "the confirmed delete removes the row",
          p11.get("ok") is True
          and not any(r["name"] == "گواه-r67" for r in list_contacts()))
    p12 = report("مخاطب گواه-ناموجود-zz را حذف کن — تأیید کن")
    check(12, "an unknown contact name is an honest refusal",
          p12.get("ok") is False and "ندارم" in str(p12.get("agent_report", "")))

    # cleanup
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r67%'")
    db.execute("DELETE FROM contacts WHERE name LIKE '%گواه-r67%'")

    print()
    if FAILURES:
        print(f"R67 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R67 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
