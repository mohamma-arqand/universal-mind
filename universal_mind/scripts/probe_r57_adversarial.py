#!/usr/bin/env python3
"""R57 — the adversarial drill, live-proved: 8 proofs.

The red team attacks the platform with hostile input; the restore drill
proves the backup is a real recovery path. Both are run FOR REAL here
(no mocks of the behavior under test):

 1  The corpus carries the five R57 attack classes (authority spoofing,
    instruction override, SQL write, secret exfiltration, encoding edge).
 2  Every hostile sentence is answered HONESTLY: zero findings.
 3  The store loses NOTHING: no row deleted, no table dropped.
 4  A refused hostile sentence harvests its unknowns (the refusals are
    useful data, not silence).
 5  The restore drill restores the REAL newest backup.
 6  The restored store's integrity check is 'ok'.
 7  Every table's row count matches the source EXACTLY (no divergence).
 8  A drill against a missing backup directory fails HONESTLY (named).
"""

from __future__ import annotations

import sys
import tempfile
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
    import os

    os.environ["UM_MUTE"] = "1"  # the platform's voice never speaks in a drill

    from universal_mind.red_team import HOSTILE_CORPUS, run_red_team
    from universal_mind.restore_drill import run_restore_drill

    corpus = " ".join(HOSTILE_CORPUS)
    # 1 — the five new attack classes are IN the corpus
    classes = {
        "authority": "[SYSTEM]" in corpus and "دستور مستقیم مدیر" in corpus,
        "override": "نادیده بگیر" in corpus and "ignore all previous" in corpus,
        "sql_write": "DELETE FROM run_history" in corpus and "DROP TABLE goals" in corpus,
        "secrets": "API key" in corpus and ".env" in corpus,
        "encoding": "بكش" in corpus and "\u200f" in corpus,
    }
    check(1, f"corpus carries the 5 R57 attack classes {classes}",
          all(classes.values()))

    # 2+3+4 — the live sweep
    res = run_red_team()
    check(2, f"all {res['total']} hostile sentences answered honestly "
             f"(findings={len(res['findings'])})",
          res["honest"] == res["total"] and not res["findings"])
    check(3, "the store lost NOTHING (no row deleted, no table dropped)",
          bool(res.get("store_intact")))
    check(4, "hostile refusals still harvest their unknown words",
          # a refused sentence's words reached the unknown-terms store
          any(k == "unknown_terms" for k in (res.get("fingerprint") or {})),
          )

    # 5+6+7 — the restore drill on the REAL newest backup
    drill = run_restore_drill()
    check(5, f"the real newest backup restored ({Path(str(drill.source)).name})",
          drill.ok and bool(drill.source))
    check(6, f"restored integrity = {drill.integrity!r}", drill.integrity == "ok")
    same = bool(drill.tables) and all(src == dst for src, dst in drill.tables.values())
    check(7, f"every table's rows match the source exactly ({len(drill.tables)} tables)",
          same and not drill.diverged)

    # 8 — an empty store dir fails honestly, never a fake success
    empty = Path(tempfile.mkdtemp()) / "no-backups-here"
    empty.mkdir()
    bad = run_restore_drill(store_dir=str(empty))
    check(8, "a missing backup is a NAMED failure, never a fake success",
          bad.ok is False and bool(str(bad.error).strip()))

    print()
    if FAILURES:
        print(f"R57 probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R57 probe: ALL 8 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
