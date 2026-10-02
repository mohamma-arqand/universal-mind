#!/usr/bin/env python3
"""Generate docs/COMMANDS.md from the router's own vocabulary — one truth.

The command book is DERIVED, never hand-written: capability names and
sample commands come from _VOCAB and the registry; the counts come from
the registry itself. Run after any vocabulary change:
    python scripts/gen_commands.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def main() -> int:
    from universal_mind.persian_router import _VOCAB
    from universal_mind.persian_report import _CAP_FA
    from universal_mind.real_tool_registry import real_tool_registry

    caps = sorted(real_tool_registry().capabilities())
    by_cap: dict[str, list[str]] = {c: [] for c in caps}
    for word, cap in _VOCAB:
        if cap in by_cap and word not in by_cap[cap]:
            by_cap[cap].append(word)

    lines = [
        "# فرماننامه — همهی فرمانهای فارسی ذهن جهانی",
        "",
        "> این سند از خودِ جدول واژگان روتر (`persian_router._VOCAB`) و "
        "رجیستری واقعی تولید شده — منبع حقیقت، نه فهرست دستی. "
        "هر تغییر در کد، با `python scripts/gen_commands.py` این جدول را هم به‌روز میکند.",
        "",
        f"## قابلیتها ({str(len(caps)).translate(_FA)})",
        "",
        "| قابلیت | واژههای فرمان |",
        "|---|---|",
    ]
    for c in caps:
        fa = _CAP_FA.get(c, c)
        words = by_cap.get(c) or []
        sample = "، ".join(f"«{w}»" for w in words[:6]) or "—"
        lines.append(f"| **{fa}** | {sample} |")

    lines += [
        "",
        "## حالتهای ویژه (mode-verbs — قبل از هر مسیری)",
        "",
        "| فرمان | اثر |",
        "|---|---|",
        "| **«بیصدا»** | پلتفرم برای همیشه بیصدا میشود (رکورد ماندگار) |",
        "| **«باز صدا»** | صدا برمیگردد |",
        "",
        "## یادآوریها",
        "",
        "| فرمان | اثر |",
        "|---|---|",
        "| «یادم بنداز/باشه/باشی فردا ساعت ۸ …» | یادآور یکبارمصرف |",
        "| «یادآور کن هر روز ساعت ۸ …» | یادآور تکرارشونده |",
        "| «یادآورهای من» | فهرست شمارهدار |",
        "| «یادآوری N را حذف کن» | حذف با شماره |",
        "| «همه یادآوریها را حذف کن — تأیید کن» | حذف گروهی (قانون حذف) |",
        "",
    ]

    out = ROOT / "docs" / "COMMANDS.md"
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"COMMANDS.md regenerated: {len(caps)} capabilities, "
          f"{sum(len(v) for v in by_cap.values())} vocabulary words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
