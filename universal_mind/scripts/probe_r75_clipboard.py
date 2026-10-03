#!/usr/bin/env python3
"""R75 — the CLIPBOARD sweep: 10 live proofs.

A 12-command sweep found 10 wrong answers (greeting for a copy ask;
file-move for a text copy; a file READ for a path copy) plus the system
discovery: the machine's clipboard is PERMANENTLY held by cua-driver.
The honest lock NAMES the holder; the copy family follows the
sentence's object.
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
    from universal_mind.persian_params import extract_params
    from universal_mind.persian_router import route_and_run

    # 1-4 — the copy family follows the sentence's object
    p = route_and_run("متن «سلام به همه» را در کلیپبورد کپی کن")
    check(1, f"quoted text copy is clipboard-only ({p.get('route')})",
          p.get("route") == ["clipboard"])
    p = route_and_run("سلام به همه را کپی کن")
    check(2, f"a greeting-shaped copy is WORK ({p.get('route')})",
          p.get("route") == ["clipboard"])
    p = route_and_run("سلام")
    check(3, "the plain greeting still greets",
          p.get("ok") is True and "conversational" in (p.get("route") or []))
    got = extract_params("آدرس فایل D:/g/x.txt را کپی کن", "clipboard")
    check(4, f"a path copy carries the PATH as the payload ({got.get('text')!r})",
          got.get("operation") == "write" and got.get("text") == "D:/g/x.txt")

    # 5-6 — the payload shapes
    got = extract_params("متن را در کلیپبورد بگذار: متن آزمایشی", "clipboard")
    check(5, "the colon payload rides", got == {"operation": "write",
                                                "text": "متن آزمایشی"})
    got = extract_params("محتوای کلیپبورد را بخوان", "clipboard")
    check(6, "a read ask reads", got == {"operation": "read"})

    # 7 — a REAL file copy (path + به) still copies the file
    base = Path(r"D:/gwr75_probe")
    base.mkdir(exist_ok=True)
    src = base / "a.txt"
    src.write_text("g75", encoding="utf-8")
    (base / "dst").mkdir(exist_ok=True)
    for f in (base / "dst").iterdir():
        f.unlink()
    p = route_and_run(f"فایل {src} را به پوشه {base / 'dst'} کپی کن")
    check(7, "a file copy with a folder destination still copies",
          p.get("ok") is True and (base / "dst" / "a.txt").exists())

    # 8-10 — the honest lock
    from universal_mind.real_clipboard import ClipboardTool, _clipboard_holder

    holder = _clipboard_holder()
    check(8, f"the holder is NAMED when visible ({holder!r})",
          isinstance(holder, str) and (holder == "" or "برنامهٔ" in holder))
    out = ClipboardTool().set_text("probe-r75")
    if out["ok"]:
        check(9, "clipboard free: the write really happened", True)
        check(10, "…and reads back the same text",
              ClipboardTool().get_text().get("outcome") == "probe-r75")
    else:
        err = out["error"]
        named = ("برنامهٔ" in err) or ("برنامهی دیگر" in err)
        check(9, f"the lock is honestly NAMED (holder: {holder[:30]})",
              "کلیپبورد قفل شده" in err and named)
        check(10, "the read side names the lock too",
              "کلیپبورد قفل شده" in ClipboardTool().get_text().get("error", ""))

    print()
    if FAILURES:
        print(f"R75 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R75 probe: ALL 10 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
