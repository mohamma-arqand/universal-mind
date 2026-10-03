#!/usr/bin/env python3
"""R64 — the correction/counting/editing sweep's fixes, live-proved: 12 proofs.

The 16-command sweep measured 9 classes (three of them LIVE LIES - real
numbers about the wrong thing); P1-P9 closed them. This probe re-runs
the REAL sentences:

 1  «چند تا یادآور دارم؟» counts SCHEDULES, never run_history.
 2  A word count answers from learned_vocab (or the honest empty).
 3  A file count answers from the textfile runs.
 4  «۵ منهای ۹ را حساب کن» is SUBTRACTION (−۴), never a mean.
 5  «۵ منهای ۹ چند می‌شود؟» reaches the compute engine.
 6  «کمک» answers with the capability list.
 7  «اشتباه شد، لغو کن» is the honest cancel (or the empty-store refusal).
 8  A pleasantry is stripped from the stored reminder and acknowledged.
 9  File SEARCH returns real matches with line numbers.
10  File REPLACE without confirmation refuses with the remedy.
11  File REPLACE with confirmation really rewrites (count + content).
12  «نه منظورم دیشب بود» refuses the past by name.
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
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.persian_router import route_and_run

    def report(cmd: str) -> str:
        return str(route_and_run(cmd).get("agent_report", ""))

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")
    db.execute("DELETE FROM learned_vocab WHERE word = 'زرشک-r64'")

    # 1-3 — the real counts
    route_and_run("یادم باشه فردا ساعت ۷ گواه-r64 را بدهکار کن")
    r1 = report("چند تا یادآور دارم؟")
    check(1, "the reminder count comes from schedules",
          "یادآور داری" in r1 and "اجرا ثبت شده" not in r1)
    from universal_mind.learned_vocab import teach

    teach("زرشک-r64", "داده")
    r2 = report("چند تا واژه از من یاد گرفتی؟")
    check(2, "the word count comes from learned_vocab",
          "واژه" in r2 and "زرشک-r64" in r2)
    r3 = report("چند تا فایل تا حالا ساختی؟")
    check(3, "the file count comes from the file runs",
          ("فایل نوشتهام" in r3) and "اجرا ثبت شده" not in r3)
    db.execute("DELETE FROM learned_vocab WHERE word = 'زرشک-r64'")

    # 4-5 — real subtraction
    r4 = report("۵ منهای ۹ را حساب کن")
    check(4, "subtraction is subtraction, never a mean",
          "نتیجه -۴" in r4 and "میانگین" not in r4)
    r5 = report("۵ منهای ۹ چند می‌شود؟")
    check(5, "the «چند می‌شود؟» shape reaches the engine",
          "نتیجه -۴" in r5 and "نشناختم" not in r5)

    # 6-7 — the spoken gates
    r6 = report("کمک")
    check(6, "«کمک» answers with the capability list",
          "قابلیت" in r6 and "نشناختم" not in r6)
    route_and_run("جمع ۲ و ۳ را حساب کن")
    r7 = report("اشتباه شد، لغو کن")
    check(7, "the prefix cancel is the honest cancel",
          ("لغوِ خودکار نمی‌کنم" in r7 or "پیدا نکردم" in r7)
          and "نشناختم" not in r7)

    # 8 — the pleasantry
    route_and_run("خسته نباشی، یادم باشه فردا ساعت ۹ گواه-r64 را بدهکار کن")
    q8 = db.query("SELECT command FROM schedules WHERE command LIKE '%گواه-r64%'")
    rows8 = q8.get("rows", []) if q8.get("ok") else []
    check(8, "the pleasantry never rides into the stored reminder",
          rows8 and "خسته نباشی" not in rows8[-1]["command"])

    # 9-11 — the file operations (real witness file)
    witness = Path("D:/um_r64_probe.txt")
    witness.write_text("سلام دنیا\nاین یک سلام است\nمتن آزمون", encoding="utf-8")
    r9 = report(f"در فایل {witness} دنبال کلمه سلام بگرد")
    check(9, "file search returns matches with line numbers",
          "۲ مورد" in r9 and "خط ۱" in r9 and "خط ۲" in r9)
    before = witness.read_text(encoding="utf-8")
    r10 = report(f"فایل {witness} را ویرایش کن و کلمه سلام را با درود عوض کن")
    check(10, "replace without confirmation refuses and touches nothing",
          "تأیید" in r10 and witness.read_text(encoding="utf-8") == before)
    r11 = report(f"روی همان فایل {witness} کلمه سلام را با درود عوض کن")
    after = witness.read_text(encoding="utf-8")
    witness.unlink()
    check(11, "replace with confirmation really rewrites",
          "۲ مورد عوض شد" in r11 and "درود دنیا" in after and "سلام" not in after)

    # 12 — the past correction
    r12 = report("نه منظورم دیشب بود")
    check(12, "a past correction refuses by name",
          "گذشته" in r12 and "نمی‌توان" in r12)

    db.execute("DELETE FROM schedules WHERE command LIKE '%گواه-r64%'")

    print()
    if FAILURES:
        print(f"R64 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R64 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
