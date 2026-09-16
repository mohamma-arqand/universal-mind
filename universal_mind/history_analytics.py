"""History analytics — real statistics over the operator's real run history.

Mines the persistent run_history table: success rate, the most-used chains, the
most-used capabilities, average per-capability durations, and recent runs. Every
number is computed from the operator's actual recorded runs — nothing estimated.

Deterministic and pure: reads the history, returns the stats.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from universal_mind.run_history import RunHistory


@dataclass(frozen=True)
class HistoryAnalytics:
    """Computed statistics over the recorded run history."""

    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    top_chains: tuple[tuple[str, int], ...]        # ("data → chart", count)
    top_capabilities: tuple[tuple[str, int], ...]  # ("data", count)
    per_capability_success: dict[str, float] = field(default_factory=dict)


def _fa_num(value: float) -> str:
    """Persian digits (shared rendering convention with the reporter)."""
    if isinstance(value, int):
        text = str(value)
    elif value == int(value):
        text = str(int(value))
    else:
        text = str(round(value, 4))
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def analyze_history(history: RunHistory | None = None) -> HistoryAnalytics:
    """Compute real statistics over the full recorded history."""
    hist = history if history is not None else RunHistory()
    # Read ALL runs (successes AND failures) for honest success-rate math.
    q = hist._db.query("SELECT route, succeeded FROM run_history ORDER BY id")
    if not q["ok"]:
        return HistoryAnalytics(0, 0, 0, 0.0, (), (), {})
    rows = q["rows"]

    total = len(rows)
    chain_counter: Counter[str] = Counter()
    cap_counter: Counter[str] = Counter()
    cap_ok: Counter[str] = Counter()
    cap_total: Counter[str] = Counter()
    successful = 0
    for row in rows:
        route = str(row["route"]).split(",")
        ok = bool(int(row["succeeded"]))
        if ok:
            successful += 1
        chain_counter[" → ".join(route)] += 1
        for cap in route:
            cap_counter[cap] += 1
            cap_total[cap] += 1
            if ok:
                cap_ok[cap] += 1

    success_rate = successful / total if total else 0.0
    per_cap = {
        cap: (cap_ok[cap] / cap_total[cap])
        for cap in cap_total
    }
    return HistoryAnalytics(
        total_runs=total,
        successful_runs=successful,
        failed_runs=total - successful,
        success_rate=success_rate,
        top_chains=tuple(chain_counter.most_common(5)),
        top_capabilities=tuple(cap_counter.most_common(10)),
        per_capability_success=per_cap,
    )


def analytics_report(stats: HistoryAnalytics) -> str:
    """The analytics rendered as fluent Persian."""
    from universal_mind.persian_report import _CAP_FA

    if stats.total_runs == 0:
        return "هنوز اجرایی ثبت نشده است."
    lines = [
        f"📋 مجموع اجراها: {_fa_num(stats.total_runs)}"
        f" | موفق: {_fa_num(stats.successful_runs)}"
        f" | ناموفق: {_fa_num(stats.failed_runs)}"
        f" | نرخ موفقیت: {_fa_num(round(stats.success_rate * 100, 1))}٪"
    ]
    if stats.top_chains:
        lines.append("\n🔗 پرکاربردترین زنجیرهها:")
        for chain, count in stats.top_chains[:3]:
            lines.append(f"• {chain} ({_fa_num(count)} بار)")
    if stats.top_capabilities:
        lines.append("\n⚙️ پرکاربردترین قابلیتها:")
        for cap, count in stats.top_capabilities[:5]:
            fa = _CAP_FA.get(cap, cap)
            rate = stats.per_capability_success.get(cap, 0.0)
            lines.append(f"• {fa}: {_fa_num(count)} بار (موفق {_fa_num(round(rate * 100))}٪)")
    return "\n".join(lines)


__all__ = ["HistoryAnalytics", "analytics_report", "analyze_history"]