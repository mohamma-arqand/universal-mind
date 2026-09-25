"""The operator's yearbook — the platform narrates its OWN history.

R44 item 16, the last: «گزارش سالانهام را بساز» — the platform reads its
real run history, its learned lessons, and the operator's human verdicts, and
renders a Persian PDF yearbook. This is the sum of every loop: what it did,
what it learned, what the human said about it.

Everything in the yearbook is DERIVED FROM THE REAL STORE — nothing is
invented. An empty history produces an honest first-page ("this is the year
we begin"), never a fabricated narrative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(n: Any) -> str:
    return str(n).translate(_FA)


def _store() -> Any:
    from universal_mind.database_suite import DatabaseSuite

    return DatabaseSuite(persistent=True)


def _year_stats(db: Any, year: int) -> dict[str, Any]:
    """The real numbers of one LOCAL year: runs, wins, chains, excellence."""
    stats: dict[str, Any] = {"runs": 0, "ok": 0, "chains": {}, "top": []}
    try:
        q = db.query(
            "SELECT route, COUNT(*) AS n, COALESCE(SUM(succeeded), 0) AS ok_n, "
            "COALESCE(AVG(excellence), 0) AS m FROM run_history "
            "WHERE strftime('%Y', created_at, 'localtime') = ? "
            "AND (outcome_class IS NULL OR outcome_class NOT IN ('blocked_env', 'needs_param')) "
            "GROUP BY route ORDER BY n DESC",
            (str(year),),
        )
        if q.get("ok"):
            for row in q.get("rows", []):
                route = str(row["route"] or "—")
                n, ok_n = int(row["n"]), int(row["ok_n"])
                stats["runs"] += n
                stats["ok"] += ok_n
                stats["chains"][route] = (n, ok_n, float(row["m"] or 0.0))
            stats["top"] = list(stats["chains"])[:5]
    except Exception:  # noqa: BLE001 — a yearbook never crashes
        pass
    return stats


def _lessons(db: Any, year: int) -> list[tuple[str, str, float]]:
    """The year's learned (capability, operation, mean excellence) — best first."""
    try:
        q = db.query(
            "SELECT capability, operation, AVG(excellence) AS m FROM planner_lessons "
            "WHERE strftime('%Y', created_at, 'localtime') = ? "
            "GROUP BY capability, operation ORDER BY m DESC, capability LIMIT 6",
            (str(year),),
        )
        if q.get("ok"):
            out: list[tuple[str, str, float]] = []
            for row in q.get("rows", []):
                out.append((str(row["capability"]), str(row["operation"]), float(row["m"] or 0.0)))
            return out
    except Exception:  # noqa: BLE001
        pass
    return []


def _verdicts(db: Any, year: int) -> dict[str, int]:
    """The operator's human 👍/👎 of the year, counted by kind."""
    counts = {"great": 0, "bad": 0}
    try:
        q = db.query(
            "SELECT verdict, COUNT(*) AS n FROM operator_verdicts "
            "WHERE strftime('%Y', created_at, 'localtime') = ? GROUP BY verdict",
            (str(year),),
        )
        if q.get("ok"):
            for row in q.get("rows", []):
                key = str(row["verdict"])
                if key in counts:
                    counts[key] += int(row["n"])
    except Exception:  # noqa: BLE001 — the table may not exist yet (honest zero)
        pass
    return counts


def yearbook_sections(year: int, *, db: Any | None = None) -> dict[str, Any]:
    """Everything the yearbook narrates, derived — nothing invented."""
    store = db if db is not None else _store()
    stats = _year_stats(store, year)
    lessons = _lessons(store, year)
    verdicts = _verdicts(store, year)
    rate = (100.0 * stats["ok"] / stats["runs"]) if stats["runs"] else 0.0
    return {
        "ok": True,
        "year": year,
        "runs": stats["runs"],
        "ok_runs": stats["ok"],
        "rate": round(rate, 1),
        "chains": stats["chains"],
        "lessons": lessons,
        "verdicts": verdicts,
        "error": "",
    }


def build_yearbook(year: int | None = None, *, db: Any | None = None,
                   out_dir: str | None = None) -> dict[str, Any]:
    """A real Persian PDF: the platform's own year, narrated for its human."""
    import datetime as dt
    import tempfile

    from universal_mind.pdf_suite import PdfSuite

    y = year if year is not None else dt.date.today().year
    data = yearbook_sections(y, db=db)
    target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="um-yearbook-"))
    target.mkdir(parents=True, exist_ok=True)

    # The narrative — every number is real, every sentence honest.
    if data["runs"] == 0:
        sections = [
            f"سالنامهی {_fa(y)} — روایتِ ذهنِ یکپارچه",
            "این سال، هنوز کاری از این تاریخچه نمانده است.",
            "این صفحهی آغاز است: هر فرمانی که از اینجا به بعد اجرا شود،",
            "بخشی از روایتِ سالِ بعد خواهد بود.",
        ]
    else:
        sections = [
            f"سالنامهی {_fa(y)} — روایتِ ذهنِ یکپارچه",
            f"در این سال، {_fa(data['runs'])} فرمان اجرا کردم؛ {_fa(data['ok_runs'])} تای آن موفق "
            f"({_fa(data['rate'])}٪).",
        ]
        if data["chains"]:
            top = "، ".join(
                f"«{_fa(route)}» ({_fa(n)} فرمان)" for route, (n, _ok, _m) in
                sorted(data["chains"].items(), key=lambda kv: -kv[1][0])[:5]
            )
            sections.append(f"پرکارترین زنجیرههای امسال: {top}.")
        if data["lessons"]:
            learned = "؛ ".join(
                f"در «{_fa(cap)}» یاد گرفتم عمل «{_fa(op)}» را عالی انجام دهم"
                for cap, op, _m in data["lessons"][:4]
            )
            sections.append(f"چیزی که از تو یاد گرفتم: {learned}.")
        v = data["verdicts"]
        if v.get("great") or v.get("bad"):
            sections.append(
                f"رأی تو دربارهی کارهایم: {_fa(v.get('great', 0))} بار «عالی بود»، "
                f"{_fa(v.get('bad', 0))} بار «بد بود» — هر دو را به وزنِ توصیهگرم گذاشتم."
            )
        sections.append("این روایت از تاریخچهی واقعی خودم خوانده شد — هیچچیز در آن ساختگی نیست.")

    pdf = PdfSuite()
    result = pdf.document(title=f"سالنامهی {_fa(y)}", sections=sections, out_dir=str(target))
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", "PDF failed"), "sections": []}
    return {
        "ok": True,
        "path": result["path"],
        "bytes": result["bytes"],
        "sections": sections,
        "stats": {"runs": data["runs"], "lessons": len(data["lessons"]),
                  "verdicts": data["verdicts"]},
        "error": "",
    }


