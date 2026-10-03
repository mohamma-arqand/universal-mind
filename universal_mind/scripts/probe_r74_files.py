#!/usr/bin/env python3
"""R74 — the FILE MANAGEMENT sweep: 12 live proofs.

A 16-command sweep found 9 wrong/missing answers (a copy to a folder
never copied; اکسل crashed openpyxl on a .txt; زیپ unknown; پوشه بساز
built a PDF; folder size/list sentences never reached their ops). This
probe pins the whole class live, on the real disk.
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
    import shutil

    from universal_mind.persian_router import route_and_run

    base = Path(r"D:/gwr74_probe")
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    src = base / "note.txt"
    src.write_text("سلام دنیا\nخط دوم\n", encoding="utf-8")
    tgt = base / "copy_target"
    tgt.mkdir()
    (base / "empty74").mkdir()

    # 1-2 — destinations that name a FOLDER
    p = route_and_run(f"فایل {src} را به پوشه {tgt} کپی کن")
    check(1, f"«کپی به پوشه Y» really copies (route={p.get('route')})",
          p.get("ok") is True and (tgt / "note.txt").exists())
    check(2, "the copy landed INSIDE the folder under its own name",
          (tgt / "note.txt").read_text(encoding="utf-8").startswith("سلام"))

    # 3-6 — the format converter (30th capability)
    p = route_and_run(f"فایل {src} را به CSV تبدیل کن")
    check(3, f"«به CSV تبدیل» routes convert only ({p.get('route')})",
          p.get("route") == ["convert"] and src.with_suffix(".csv").exists())
    p = route_and_run(f"فایل {src} را به اکسل تبدیل کن")
    ok4 = p.get("ok") is True and src.with_suffix(".xlsx").exists() and "excel" not in p["route"]
    check(4, "«به اکسل تبدیل» builds a real xlsx (openpyxl never crashes)", ok4)
    p = route_and_run(f"از فایل {src} خروجی JSON بگیر")
    check(5, "«خروجی JSON» builds a real json",
          p.get("ok") is True and src.with_suffix(".json").exists())
    from universal_mind.format_converter import convert_format

    bad = convert_format(str(src), "pdf")
    check(6, "an unsupported target is a NAMED refusal",
          bad.get("ok") is False and "پشتیبانی نمیشود" in bad.get("error", ""))

    # 7-9 — zip sentences
    for z in base.glob("*.zip"):
        z.unlink()
    p = route_and_run(f"فایل {src} را ZIP کن")
    check(7, f"«فایل X را ZIP کن» is a zip ask ({p.get('route')})",
          "zip" in (p.get("route") or []) and "archive" not in (p.get("route") or [])
          and p.get("ok") is True)
    p = route_and_run(f"پوشه {tgt} را زیپ کن")
    check(8, "«پوشه را زیپ کن» packs (folder zip)",
          p.get("ok") is True)
    from universal_mind.zip_helper import pack_folder

    empty = pack_folder(base / "empty74")
    check(9, "an empty folder is a NAMED refusal",
          "error" in empty and "خالی" in empty.get("error", ""))

    # 10-12 — folder asks own their sentence
    (base / "گزارشها").rmdir() if (base / "گزارشها").exists() else None
    p = route_and_run("یک پوشه به نام گزارشها در D:/gwr74_probe بساز")
    check(10, f"«پوشه به نام X بساز» builds the folder, never a PDF ({p.get('route')})",
          p.get("ok") is True and (base / "گزارشها").exists() and "pdf" not in p["route"])
    p = route_and_run(f"حجم پوشه {base} چنده؟")
    rep = str(p.get("agent_report", ""))
    check(11, f"«حجم پوشه» answers the real stats ({rep[rep.find('•'):rep.find('•')+50] if '•' in rep else 'no bullet'})",
          p.get("ok") is True and "فایل" in rep and "بایت" in rep)
    p = route_and_run(f"همه فایلهای txt پوشه {base} را فهرست کن")
    rep = str(p.get("agent_report", ""))
    check(12, "«فایلهای txt پوشه» lists with the pattern filter",
          p.get("ok") is True and "note.txt" in rep)

    shutil.rmtree(base, ignore_errors=True)
    print()
    if FAILURES:
        print(f"R74 probe FAILED ({len(FAILURES)}):")
        for x in FAILURES:
            print(f"  ✗ {x}")
        return 1
    print("R74 probe: ALL 12 LIVE PROOFS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
