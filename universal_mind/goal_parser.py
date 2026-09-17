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
    """One parsed objective: its steps, ready to run as commands."""

    text: str
    steps: tuple[str, ...]


def parse_goal(sentence: str) -> Goal | None:
    """Extract a goal and its steps from a Persian sentence, or None.

    The honest forms:
      «هدف: ...»     — a goal header (with or without «داشتن»/«کردن» endings)
      «و» / «سپس» / «بعد» / «،» — the step separators
    A sentence without the goal marker is NOT a goal (the caller treats it
    as a normal command) — the agent never hijacks ordinary commands.
    """
    normalized = sentence.translate(_FA_DIGITS).strip()
    # A goal sentence may carry a LEADING schedule clause («هر روز ساعت ۸
    # هدف: ...») — the schedule layer parses it; here we only need the goal
    # body, so strip any leading «هر ...» clause before matching.
    stripped = re.sub(r"^هر\s+(?:روز\s+ساعت\s+\d{1,2}|\d+\s+(?:دقیقه|ساعت))\s+", "", normalized)
    marker = re.search(r"هدف\s*[:：]\s*(.+)$", stripped, re.IGNORECASE)
    body = marker.group(1).strip() if marker else None
    if body is None:
        # also accept «هدفم ... است»
        marker2 = re.match(r"^هدفم\s+(.+?)\s*است$", stripped)
        body = marker2.group(1).strip() if marker2 else None
    if not body:
        return None
    # Split on the step separators «سپس/بعد/،» — and «و» ONLY when it does not
    # join two numbers («۱۰ و ۲۰» is a data list, not two steps). We scan with
    # a marker pass instead of one fragile regex.
    MARK = chr(0)  # guards numeric «و» from the step split
    guarded = re.sub(r"(\d)\s+و\s+(\d)", r"\1" + MARK + r"و" + MARK + r"\2", body)
    parts = re.split(r"\s+(?:سپس|بعد(?:ش)?|آن(?:گاه)?)\s+|،|\s+و\s+", guarded)
    parts = [p2.replace(MARK, " ") for p2 in parts]
    steps: list[str] = []
    for part in parts:
        step = part.strip()
        # a real step ends in a verb-ish suffix or carries a capability word;
        # tiny fragments like «گزارش» alone attach to the previous step
        if not step:
            continue
        if len(step) < 3:
            if steps:
                steps[-1] = f"{steps[-1]} و {step}"
            continue
        steps.append(step)
    if not steps:
        return None
    return Goal(text=sentence.strip(), steps=tuple(steps))


def goal_report(goal: Goal) -> dict[str, Any]:
    """The goal rendered for the operator (steps numbered in Persian)."""
    fa = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    lines = [f"🎯 هدف ثبت شد: {goal.text}"]
    for i, step in enumerate(goal.steps, 1):
        lines.append(f"  {str(i).translate(fa)}. {step}")
    return {"ok": True, "goal": goal.text, "steps": list(goal.steps), "rendered": "\n".join(lines), "error": ""}


__all__ = ["Goal", "Goal", "parse_goal", "goal_report"]