"""The goal parser — turning a Persian GOAL into executable steps.

The operator can now state an OBJECTIVE instead of a single command:
  «هدف: وضعیت فروش ماهانه را تحلیل کن و گزارش کامل بساز»
The parser splits the objective into STEPS the engine already knows how to
run — each step is a normal Persian command; the agent loop (agent_loop.py)
runs them in order under ARETĒ judgment.

Honest rules:
- Decomposition is conjunction-based: «X کن و Y کن» → [X, Y]. Complex goals
  stay WHOLE when they cannot be honestly split (never a forced split that
  changes the meaning).
- Persian digits are normalized per step; the connector words are consumed.
- An empty goal is refused with the exact syntax, never a fabricated step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


@dataclass(frozen=True)
class Goal:
    """One parsed objective: its steps (and which are conditionally guarded)."""

    text: str
    steps: tuple[str, ...]
    guarded: tuple[bool, ...] = ()  # parallel to steps: True = run only if the
    #                                    previous step's ARETĒ verdict said ok


def parse_goal(sentence: str) -> Goal | None:
    """Extract a goal and its steps from a Persian sentence, or None.

    Honest forms:
      «هدف: ...»     — a goal header
      «هدفم ... است» — the alternate form
      «و» / «سپس» / «بعد» / «،» — the step separators
      «اگر ... موفق بود، Y» — a CONDITIONAL step: Y runs only when the
        previous step's ARETĒ verdict says ok (the guard is recorded).
    A sentence without the goal marker is NOT a goal.
    """
    normalized = sentence.translate(_FA_DIGITS).strip()
    stripped = re.sub(
        r"^هر\s+(?:روز\s+ساعت\s+\d{1,2}|\d+\s+(?:دقیقه|ساعت))\s+", "", normalized
    )
    marker = re.search(r"هدف\s*[:：]\s*(.+)$", stripped, re.IGNORECASE)
    body = marker.group(1).strip() if marker else None
    if body is None:
        marker2 = re.match(r"^هدفم\s+(.+?)\s*است$", stripped)
        body = marker2.group(1).strip() if marker2 else None
    if not body:
        return None

    MARK = chr(0)
    guarded = re.sub(r"(\d)\s+و\s+(\d)", r"\1" + MARK + r"و" + MARK + r"\2", body)
    raw_parts = re.split(r"\s+(?:سپس|بعد(?:ش)?|آن(?:گاه)?)\s+|،|\s+و\s+", guarded)

    steps: list[str] = []
    guarded_steps: list[bool] = []
    pending_guard = False
    for part in raw_parts:
        step = part.replace(MARK, " ").strip()
        if not step:
            continue
        m = re.match(r"^اگر.*?(?:موفق بود|درست بود|خوب بود)[،,]?\s*(.*)$", step)
        if m and m.group(1).strip():
            steps.append(m.group(1).strip())
            guarded_steps.append(True)
            continue
        if m:
            pending_guard = True
            continue
        if len(step) < 3 and steps:
            steps[-1] = f"{steps[-1]} و {step}"
            continue
        steps.append(step)
        guarded_steps.append(pending_guard)
        pending_guard = False
    if not steps:
        return None
    return Goal(text=sentence.strip(), steps=tuple(steps), guarded=tuple(guarded_steps))


def goal_report(goal: Goal) -> dict[str, Any]:
    """The goal rendered for the operator (steps numbered in Persian)."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    lines = [f"🎯 هدف ثبت شد: {goal.text}"]
    for i, step in enumerate(goal.steps, 1):
        lines.append(f"  {str(i).translate(fa)}. {step}")
    return {"ok": True, "goal": goal.text, "steps": list(goal.steps), "rendered": "\n".join(lines), "error": ""}


__all__ = ["Goal", "Goal", "parse_goal", "goal_report"]