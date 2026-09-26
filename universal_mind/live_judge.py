"""The LIVE judge — a second opinion from a real model outside the formula.

R47 item 1: ARETĒ grades every run with its virtue formula — but a mind
that only self-assesses has one blind spot: it never meets a foreign
standard. This module sends the command + the run's report + the formula's
own verdict to a LIVE model (through the same env-wired LLMToolConnector)
and asks for an independent score (0..1) with one line of reason.

Honesty rules (the same law as every R45/R46 addition):
  - no env (UM_LLM_BASE_URL) → the live judge says so and REFUSES —
    never a mock score, never a fabricated verdict;
  - a malformed reply → refused, the raw text kept in the reason;
  - every real verdict lands in `live_judgments` (formula vs live, side
    by side) — divergence > 0.3 is the drift signal of the formula itself.
"""

from __future__ import annotations

import json
from typing import Any

from universal_mind.database_suite import DatabaseSuite

_PROMPT = """تو یک داورِ مستقل برای یک پلتفرم فارسی هستی. این اجرا را مستقل از هر معیاری نمره بده.

فرمان اپراتور:
{command}

گزارشی که پلتفرم به اپراتور داد:
{report}

نمرهی داوری داخلی پلتفرم (فرمول ARETĒ): {formula:.2f}

مهمات (کیفیت، صداقت، فایده) را خودت بسنج. فقط JSON برگردان، بدون هیچ متن دیگری:
{{"score": <عدد بین 0 و 1>, "reason": "<یک جملهی فارسی کوتاه>"}}
"""


def ensure_table(db: DatabaseSuite) -> None:
    db.ensure_schema("live_judgments", [
        "CREATE TABLE IF NOT EXISTS live_judgments ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "command TEXT NOT NULL, formula_score REAL NOT NULL, "
        "llm_score REAL NOT NULL, reason TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')))",
    ])


def judge_live(command: str, report: str, formula_score: float, *,
               db: DatabaseSuite | None = None) -> dict[str, Any]:
    """Ask a real model for an independent verdict. Refused when env is absent.

    Returns {"ok": bool, "llm_score": float, "reason": str, "diverged": bool}.
    """
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    from universal_mind.llm_connector import LLMToolConnector

    prompt = _PROMPT.format(command=command[:300], report=report[:800],
                            formula=float(formula_score))
    res = LLMToolConnector().connect({}, {"prompt": prompt, "max_tokens": 200,
                                          "timeout": 30})
    if not res.ok:
        return {"ok": False, "llm_score": 0.0,
                "reason": f"داورِ زنده در دسترس نیست — {res.error}", "diverged": False}

    # parse the JSON reply (tolerant: strip code fences, find the braces)
    text = str((res.output or {}).get("text", "")).strip()
    raw = text
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        payload = json.loads(raw[start:end])
        score = float(payload.get("score"))
        reason = str(payload.get("reason", "")).strip()
        if not 0.0 <= score <= 1.0:
            raise ValueError("نمره بیرون از بازه است")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {"ok": False, "llm_score": 0.0,
                "reason": f"پاسخ مدل شکلِ شناخته نداشت ({exc}): {text[:120]}",
                "diverged": False}

    diverged = abs(score - float(formula_score)) > 0.3
    store.insert_many("live_judgments", [{
        "command": command,
        "formula_score": f"{float(formula_score):.4f}",
        "llm_score": f"{score:.4f}",
        "reason": reason,
    }])
    return {"ok": True, "llm_score": score, "reason": reason, "diverged": diverged}


def latest_live_judgments(limit: int = 5, *,
                          db: DatabaseSuite | None = None) -> list[dict[str, Any]]:
    """The newest live verdicts — what the day's summary reads."""
    store = db or DatabaseSuite.shared_persistent()
    ensure_table(store)
    q = store.query(
        "SELECT command, formula_score, llm_score, reason, created_at "
        f"FROM live_judgments ORDER BY id DESC LIMIT {int(limit)}"
    )
    rows = q.get("rows", []) if q.get("ok") else []
    return [
        {"command": str(r["command"]),
         "formula": float(r["formula_score"]),
         "llm": float(r["llm_score"]),
         "reason": str(r["reason"]),
         "created_at": str(r["created_at"])}
        for r in rows
    ]


__all__ = ["ensure_table", "judge_live", "latest_live_judgments"]
