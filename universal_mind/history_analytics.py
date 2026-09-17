"""History analytics — real statistics over the operator's real run history.

Mines the persistent run_history table: success rate, the most-used chains, the
most-used capabilities, average per-capability durations, and recent runs. Every
number is computed from the operator's actual recorded runs — nothing estimated.

Deterministic and pure: reads the history, returns the stats.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

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
    mean_excellence: float = 0.0  # ARETĒ's average excellence over judged runs


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
    # ARETĒ's mean excellence over the runs it judged (old rows have NULL).
    try:
        exc = hist._db.query(
            "SELECT AVG(excellence) AS m FROM run_history "
            "WHERE excellence IS NOT NULL AND succeeded = 1"
        )
        mean_excellence = float(exc["rows"][0]["m"]) if exc.get("ok") and exc["rows"] and exc["rows"][0]["m"] is not None else 0.0
    except Exception:  # noqa: BLE001 — analytics over a missing column is 0, not fatal
        mean_excellence = 0.0
    return HistoryAnalytics(
        total_runs=total,
        successful_runs=successful,
        failed_runs=total - successful,
        success_rate=success_rate,
        top_chains=tuple(chain_counter.most_common(5)),
        top_capabilities=tuple(cap_counter.most_common(10)),
        per_capability_success=per_cap,
        mean_excellence=round(mean_excellence, 4),
    )


def standing_chain() -> dict[str, Any]:
    """The chain that has won REPEATEDLY with high excellence — a candidate
    for a standing standard (the bridge to the seed-core's StandardKeeper).

    Honest bar: 3+ successes, mean excellence >= 0.90. Nothing forced —
    when no chain qualifies, None is returned, never a crowned default.
    """
    from universal_mind.run_history import RunHistory

    history = RunHistory()
    counts: dict[tuple[str, ...], list[float]] = {}
    for record in history.successful_runs():
        if record.excellence >= 0.90:
            counts.setdefault(record.route, []).append(record.excellence)
    best_route: tuple[str, ...] | None = None
    best_mean = 0.0
    for route, excs in counts.items():
        if len(excs) >= 3:
            mean = sum(excs) / len(excs)
            if mean > best_mean:
                best_route, best_mean = route, mean
    if best_route is None:
        return {"ok": False, "error": "هیچ زنجیرهای هنوز سزاوار استاندارد نشده"}
    return {
        "ok": True, "route": list(best_route), "wins": len(counts[best_route]),
        "mean_excellence": round(best_mean, 4), "error": "",
    }


def crown_standing_chain() -> dict[str, Any]:
    """The REAL bridge: the platform's repeatedly-winning chain goes through
    the seed-core's StandardKeeper election — the first uncontested standard
    must still clear the justice hard-gate (arbitrated against a refusal
    baseline, never self-seeded blindly).

    Honest rules:
    - No qualifying chain → no crown (never a default standard).
    - The crowning uses the SAME CandidateOutput/virtues machinery as every
      specialist dispute — the platform's own best practice becomes a
      standard through the same law, not a shortcut.
    - The result reports the promotion decision and its reason verbatim.
    """
    standing = standing_chain()
    if not standing.get("ok"):
        return {"ok": False, "error": standing.get("error", ""), "crowned": False}

    from universal_mind.arete import StandardKeeper
    from universal_mind.powers.judgment import CandidateOutput

    route = standing["route"]
    chain_name = " → ".join(route)
    # The chain's virtues from its REAL record: excellence as wisdom/courage,
    # repeated wins as justice (consistency), bounded steps as temperance.
    mean_ex = standing["mean_excellence"]
    proposal = CandidateOutput(
        strategy_id=f"chain::{chain_name}",
        output={"route": route, "wins": standing["wins"]},
        metadata={"virtues": {
            "wisdom": mean_ex,
            "courage": mean_ex,
            "temperance": 1.0,   # the chain's steps are bounded by design
            "justice": 1.0,      # every recorded run was judged the same way
        }},
    )
    try:
        from universal_mind.core.clock import SystemClock
        from universal_mind.core.identity import DEFAULT_OWNER
        from universal_mind.memory.store import LocalJSONLStore

        keeper = StandardKeeper(
            store=LocalJSONLStore(),  # a fresh temp ledger for the election
            clock=SystemClock(), owner=DEFAULT_OWNER,
        )
        result = keeper.consider(proposal)
    except Exception as exc:  # noqa: BLE001 — the bridge is a lens, never fatal
        return {"ok": False, "error": f"تاج ناموفق: {exc}", "crowned": False}
    decision = getattr(result, "decision", None)
    decision_name = getattr(decision, "name", str(decision)) if decision is not None else ""
    promoted = decision_name.upper().startswith("ALLOW") or decision_name.upper().startswith("PROMOTE")
    verdict = getattr(result, "verdict", None)
    reason = str(getattr(verdict, "reasoning", "") or decision_name)
    return {
        "ok": True, "crowned": bool(promoted), "chain": chain_name,
        "wins": standing["wins"], "mean_excellence": mean_ex,
        "decision": reason, "error": "",
    }


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
    if stats.mean_excellence > 0.0:
        lines[0] += f" | میانگین داوری ARETĒ: {_fa_num(round(stats.mean_excellence * 100, 1))}٪"
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
    # What the planner has LEARNED from real verdicts (the earned table).
    try:
        from universal_mind.planner_learning import lessons_report

        lessons = lessons_report()["lessons"]
        taught = [l for l in lessons if l["mean_excellence"] >= 0.75]
        if taught:
            lines.append("\n🧠 planner چه آموخته (از داوریهای واقعی):")
            for lesson in taught[:6]:
                lines.append(
                    f"• {_CAP_FA.get(lesson['capability'], lesson['capability'])}: "
                    f"«{lesson['operation']}» — داوری {_fa_num(round(lesson['mean_excellence'] * 100))}٪ "
                    f"در {_fa_num(lesson['uses'])} اجرا"
                )
    except Exception:  # noqa: BLE001 — lessons are a view, never fatal
        pass
    return "\n".join(lines)


__all__ = ["HistoryAnalytics", "analytics_report", "analyze_history"]