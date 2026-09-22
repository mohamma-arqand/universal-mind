"""The cross-examiner — a SECOND, INDEPENDENT numeric verdict.

R44 item 5: a system graded only by its own ruler maxes out at its own
ceiling. For the numeric chains, the stats now run TWICE — once through
numpy (the production path) and once through a pure-Python reducer — and
any disagreement beyond epsilon is a live CAUGHT BUG, named and surfaced
in the Persian report. `compute` (the node engine) is the third voice when
available.

STANDARDS:
- The second verdict is INDEPENDENT: pure Python, no numpy in the path.
- A disagreement is never silent: it goes to the payload's errors and the
  Persian report names it.
- Never a blocker: if the cross-exam disagrees on an unsupported shape it
  says 'skipped', not 'failed'.
"""

from __future__ import annotations

from statistics import fmean, pstdev
from typing import Any

_EPS = 1e-9


def pure_stats(series: Any) -> dict[str, float] | None:
    """The independent second opinion — pure Python over the SAME series.

    Returns None when the shape is not examinable here (lists/arrays),
    so the cross-exam says 'skipped' instead of lying.
    """
    if isinstance(series, dict):
        inner = series.get("data") or series.get("series") or series.get("values")
        if inner is not None:
            series = inner
    if hasattr(series, "tolist"):
        series = series.tolist()
    if not isinstance(series, (list, tuple)):
        return None
    nums = [float(x) for x in series if isinstance(x, (int, float))]
    if not nums:
        return None
    return {
        "mean": fmean(nums),
        "std": pstdev(nums) if len(nums) > 1 else 0.0,
        "min": min(nums),
        "max": max(nums),
        "median": (lambda s: float(s[len(s) // 2]) if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2)(sorted(nums)),
        "count": float(len(nums)),
    }


def cross_examine(data_output: dict[str, Any]) -> dict[str, Any]:
    """Second opinion over a DataSuite.stats run — numpy vs pure Python.

    Returns {'cross_exam': {'agree': bool, 'field': str|None, ...}} — merged
    into the step's output by the caller (adaptive_orchestration).
    """
    # The data output arrives FLAT in the real route ({mean, std, min, ...}
    # at the top level, with the echoed series) or wrapped ({"stats": {...}}).
    # Both are examinable — only a shape without numbers is skipped.
    stats = (data_output or {}).get("stats")
    if not isinstance(stats, dict):
        flat = {k: v for k, v in (data_output or {}).items()
                if k in ("mean", "std", "min", "max", "median", "count")}
        if flat:
            stats = flat
    if not isinstance(stats, dict):
        return {"cross_exam": {"status": "skipped", "reason": "no stats object"}}
    series = (data_output or {}).get("_series")
    if series is None:
        series = (data_output or {}).get("data") or (data_output or {}).get("series")
    second = pure_stats(series)
    if second is None:
        return {"cross_exam": {"status": "skipped", "reason": "series not reconstructable"}}

    for field, mine in second.items():
        theirs = stats.get(field)
        if theirs is None:
            continue
        try:
            if abs(float(theirs) - float(mine)) > _EPS * max(1.0, abs(float(mine))):
                return {
                    "cross_exam": {
                        "status": "disagree",
                        "field": field,
                        "numpy": float(theirs),
                        "pure": float(mine),
                        "verdict": "باگِ شکارشده: دو داور عددی همبر نیستند",
                    }
                }
        except (TypeError, ValueError):
            continue
    return {"cross_exam": {"status": "agree", "fields": sorted(second.keys())}}


def persian_note(exam: dict[str, Any] | None) -> str | None:
    """The Persian voice of the cross-examiner, for the report."""
    if not isinstance(exam, dict):
        return None
    status = exam.get("status")
    if status == "agree":
        return "داور متقاطع عددی: دو محاسبهی مستقل همبر آمدند ✓"
    if status == "disagree":
        return (
            f"باگِ شکارشده توسط داور متقاطع عددی — «{exam.get('field')}»: "
            f"numpy {exam.get('numpy')} در برابر pure-Python {exam.get('pure')}"
        )
    return None


__all__ = ["pure_stats", "cross_examine", "persian_note"]
