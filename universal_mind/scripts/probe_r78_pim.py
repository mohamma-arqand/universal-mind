#!/usr/bin/env python3
"""R78 — the PIM sweep: 10 live proofs.

«یادداشتهایم را نشان بده» read the LOCKED clipboard (a word collision);
a contact filter listed everything; a contact's email was unknown; the
«با ایمیل» connector glued itself into the stored NAME. The wave: notes
live in named_memory (listing/forgetting), the contact class answers
filtered views and address lookups, and the stored name is clean.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    os.environ["UM_MUTE"] = "1"
    from universal_mind.database_suite import DatabaseSuite
    from universal_mind.named_memory import save_fact
    from universal_mind.persian_router import route_and_run

    db = DatabaseSuite(persistent=True)
    db.execute("DELETE FROM contacts WHERE address LIKE '%gw78p%'")
    db.execute("DELETE FROM named_memory WHERE fact LIKE '%gw78p%'")

    # 1-3 — the note class lives in named_memory, never on the clipboard
    save_fact("gw78p یادداشت اول")
    save_fact("gw78p یادداشت دوم")
    p = route_and_run("یادداشتهایم را نشان بده")
    rep = str(p.get("agent_report", ""))
    check(1, f"the note listing is reflexive ({p.get('route')})",
          p.get("route") == ["reflexive"])
    check(2, "both notes are listed from the REAL store",
          "gw78p یادداشت اول" in rep and "gw78p یادداشت دوم" in rep)
    check(3, "…and the locked clipboard is never touched",
          "کلیپبورد" not in rep)

    # 4-5 — forgetting: by name, named
    p = route_and_run("یادداشت gw78p یادداشت اول را فراموش کن")
    rep = str(p.get("agent_report", ""))
    check(4, "forgetting deletes the named note",
          "فراموش شد" in rep and "gw78p یادداشت اول" in rep
          and "gw78p یادداشت دوم" not in rep)
    p = route_and_run("یادداشت gw78pناپیدا را فراموش کن")
    check(5, "forgetting an unknown note is honest",
          "چنین یادداشتی ندارم" in str(p.get("agent_report", "")))

    # 6-7 — the contact class: clean name + address lookup
    p = route_and_run("مخاطب رضا با ایمیل r.gw78p@x.com را اضافه کن")
    rep = str(p.get("agent_report", ""))
    check(6, "the stored NAME is clean (connector stripped)",
          "«رضا»" in rep and "با ایمیل»" not in rep)
    p = route_and_run("ایمیل رضا را نشان بده")
    check(7, "«ایمیل X را نشان بده» answers the address",
          "r.gw78p@x.com" in str(p.get("agent_report", "")))

    # 8-9 — the name filter filters
    p = route_and_run("مخاطبهایی که اسمشان رضا است را پیدا کن")
    rep = str(p.get("agent_report", ""))
    check(8, "«اسمشان X» filters by the name",
          "رضا" in rep and "زهرا" not in rep and "مخاطب با نام" in rep)
    p = route_and_run("ایمیل nobodygw78p را نشان بده")
    check(9, "an unknown contact is a named miss",
          "ندارم" in str(p.get("agent_report", "")))

    # 10 — «چه چیزهایی یادت هست؟» still works (the old shape)
    p = route_and_run("چه چیزهایی یادت هست؟")
    check(10, "the old recall shape survives",
          p.get("ok") is True and "یادم است" in str(p.get("agent_report", "")))

    db.execute("DELETE FROM contacts WHERE address LIKE '%gw78p%'")
    db.execute("DELETE FROM named_memory WHERE fact LIKE '%gw78p%'")
    print()
    if FAILURES:
        print(f"R78 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R78 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
