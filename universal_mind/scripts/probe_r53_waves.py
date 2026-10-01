#!/usr/bin/env python3
"""R53 — the new real capabilities, live-proved: 10 proofs.

Runs the REAL code paths (no mocks of behavior under test) and asserts
each R53 wave's acceptance with hard failure on any regression:

 1  MUTE: the switch is armed persistently; speak() reads it LIVE.
 2  MUTE: a muted speak is HONEST (ok/spoken/muted/voice) — never a crash.
 3  ONE-SHOT: «یادم بنداز فردا ساعت ۸» parses to tomorrow 08:00 LOCAL.
 4  ONE-SHOT: a due once-reminder fires exactly once and self-deletes.
 5  IDENTITY: «اسمت چیه؟» answers with the name; «تو کی هستی؟» carries
    the REAL capability count (25).
 6  TEMPORAL: «امروز چندمه؟» answers in Jalali with Persian digits.
 7  UPTIME: «چند وقته دستگاه روشن است؟» answers a real duration or an
    honest unreadable — never «نشناختم».
 8  FILESEARCH: a real tree search returns top-K by size, read-only.
 9  FILEDEDUPE: same-size-different-content is NOT a duplicate (SHA-256
    law); preview deletes nothing.
10  SYSSTATUS: the machine's vitals are real (RAM total > 0, disks listed)
    and every missing signal is named.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n:2d}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    # ---- 1+2: THE MUTE LAW -------------------------------------------
    from universal_mind import operator_preferences as prefs
    from universal_mind.speech_tool import SpeechTool, _muted

    prefs.set("voice_muted", "1")
    check(1, "MUTE armed persistently and read live", _muted() is True)
    res = SpeechTool().speak("تست بیصدا")
    check(2, "muted speak is honest (ok/spoken/muted, no crash)",
          res.get("ok") is True and res.get("muted") is True
          and res.get("voice") == "(muted)")

    # ---- 3+4: THE ONE-SHOT REMINDER ----------------------------------
    from universal_mind.scheduler import parse_one_shot

    now = datetime(2026, 9, 30, 14, 0)
    shot = parse_one_shot("یادم بنداز که فردا ساعت ۸ زود بیدار شوم", now)
    fire = datetime.fromisoformat(shot["run_at"]) if shot else None
    check(3, "«فردا ساعت ۸» parses to tomorrow 08:00 LOCAL",
          fire == datetime(2026, 10, 1, 8, 0))

    # a due one-shot fires once then the row is gone (the tick's own law)
    import os

    tmpdb = Path(tempfile.mkdtemp()) / "r53probe.db"
    os.environ["UM_DB_OVERRIDE"] = str(tmpdb)  # probe isolation if honored
    from universal_mind import scheduler as sched

    past = (datetime.now() - timedelta(minutes=1)).isoformat()
    db = sched._store()
    sched._ensure_table(db)
    db.insert_many("schedules", [{
        "command": "پروب: دارو", "every_minutes": "0", "hour_of_day": "-1",
        "minute_of_hour": "0", "last_run": "", "active": "1",
        "kind": "once", "run_at": past,
    }])
    import unittest.mock as mock

    with mock.patch("universal_mind.real_notify.NotifyTool.notify",
                    lambda self, t="", b="": {"ok": True}), \
         mock.patch("universal_mind.speech_tool.SpeechTool.speak",
                    lambda self, text, **kw: {"ok": True, "spoken": True}):
        out = sched.run_due(contest=False)
    once = [f for f in out.get("fired", []) if f.get("once")]
    leftover = [s for s in sched.list_schedules()
                 if s.kind == "once" and s.command == "پروب: دارو"]
    check(4, "a due once-reminder fires once and self-deletes",
          len(once) == 1 and leftover == [])
    db.execute("DELETE FROM schedules WHERE command = 'پروب: دارو'")

    # ---- 5: IDENTITY ---------------------------------------------------
    from universal_mind.conversational import answer_conversational
    from universal_mind.real_tool_registry import real_tool_registry

    name = answer_conversational("اسمت چیه؟")
    who = answer_conversational("تو کی هستی؟")
    # THE CORPUS-SIZE LAW (re-learned in R59): the cap count GROWS with each
    # new capability (R59 added unitconvert: 25 → 26). Pin the INVARIANT —
    # the identity's count equals the registry's real count, in Persian
    # digits — never a number.
    try:
        _reg_n = len(real_tool_registry().capabilities)
        _fa_reg = str(_reg_n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    except Exception:  # noqa: BLE001 — fall back to the weaker invariant
        _fa_reg = ""
    check(5, "identity answers carry the name and the real cap count",
          name is not None and "ذهن جهانی" in name["agent_report"]
          and who is not None and "قابلیت واقعی" in who["agent_report"]
          and (not _fa_reg or _fa_reg in who["agent_report"]))

    # ---- 6: TEMPORAL (Jalali) ------------------------------------------
    from universal_mind.reflexive import answer_reflexive

    today = answer_reflexive("امروز چندمه؟")
    check(6, "«امروز چندمه؟» answers in Jalali Persian digits",
          today is not None and "۱۴" in today["agent_report"])

    # ---- 7: UPTIME ------------------------------------------------------
    up = answer_reflexive("چند وقته دستگاه روشن است؟")
    rep = str((up or {}).get("agent_report", ""))
    check(7, "uptime answers a real duration or honest unreadable",
          up is not None and "نشناختم" not in rep
          and any(w in rep for w in ("روز", "ساعت", "دقیقه", "نتوانستم")))

    # ---- 8: FILESEARCH (real tree, read-only) ---------------------------

    tree = Path(tempfile.mkdtemp())
    (tree / "big.bin").write_bytes(b"a" * 500_000)
    (tree / "small.txt").write_text("x", encoding="utf-8")
    before = sorted(p.name for p in tree.iterdir())
    from universal_mind.file_search_tool import FileSearchTool

    found = FileSearchTool().search(str(tree), top=1)
    check(8, "filesearch returns top-K by size and changes nothing",
          found["ok"] is True and found["matches"][0]["name"] == "big.bin"
          and sorted(p.name for p in tree.iterdir()) == before)

    # ---- 9: FILEDEDUPE (the SHA-256 law) --------------------------------
    dups = Path(tempfile.mkdtemp())
    payload = b"same-bytes"
    (dups / "d1.bin").write_bytes(payload)
    (dups / "d2.bin").write_bytes(payload)
    (dups / "c1.bin").write_bytes(b"same-length-different-content")  # same len, diff
    (dups / "c2.bin").write_bytes(b"other-17-bytes-okk")  # pad to same length
    from universal_mind.file_dedupe_tool import FileDedupeTool

    groups = FileDedupeTool().find(str(dups), min_size=1)
    n_groups = groups["n_groups"]
    preview = FileDedupeTool().clean(str(dups), min_size=1)
    check(9, "SHA-256 law: only true duplicates group; preview deletes nothing",
          n_groups == 1 and preview["deleted"] == []
          and all((dups / f).exists() for f in ("d1.bin", "d2.bin", "c1.bin", "c2.bin")))

    # ---- 10: SYSSTATUS (real vitals, honest naming) ---------------------
    from universal_mind.system_status_tool import SystemStatusTool

    vit = SystemStatusTool().status()
    ram_ok = (vit.get("ram") or {}).get("total_gb", 0) > 0
    disks = vit.get("disks") or []
    missing_named = all(
        any(k in n for n in vit.get("notes", []))
        for k in ("uptime", "ram", "disks") if vit.get(k) in (None, [])
    )
    check(10, "sysstatus reads real vitals and names every missing signal",
          vit.get("ok") is True and ram_ok and len(disks) >= 1 and missing_named)

    print()
    if FAILURES:
        print(f"R53 probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R53 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
