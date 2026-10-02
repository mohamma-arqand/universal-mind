"""The parameter A/B — an ambiguous KIND runs as a REAL contest.

R44 item 7: when the operator says «نمودارش کن» without naming the kind
(line? bar? pie?), the platform used to pick silently. Now the ambiguity
is honest: the two best-fitting variants run as REAL work (same series),
ARETĒ judges both, and the winner ships with the ruling announced in the
Persian report. A lost kind is a lesson: recorded so the next advice is
sharper.

STANDARDS:
- Only a GENUINE ambiguity contests: a named kind (میلهای/دایرهای/خطی)
  or a stored preference runs as-is — the operator's word wins, no theater.
- Both variants are real work on the same data — never a straw man.
- The ruling is visible: the report names the winner and the margin.
- Nothing is fabricated: if ARETĒ cannot separate them, the tie is said.
"""

from __future__ import annotations

from typing import Any


def kind_ambiguity(command: str, params: dict[str, Any] | None) -> bool:
    """True when the chart kind is genuinely ambiguous.

    A named kind word (خطی/میلهای/دایرهای/…) or an explicit kind_explicit
    mark means the OPERATOR chose — no ambiguity, no contest.
    """
    p = params or {}
    if p.get("kind_explicit"):
        return False
    # The kind words from extract_params' real dispatch (named kind = chosen).
    _kind_words = ("خطی", "میلهای", "میله", "ستونی", "دایرهای", "دایره",
                   "پایهای", "پراکنده", "اسکتر", "هیستوگرام", "هیستوگرامش")
    if any(w in command for w in _kind_words):
        return False
    return "نمودار" in command or "چارت" in command


def run_ab(
    command: str,
    base_params: dict[str, Any],
    run_variant: Any,  # callable(variant_params: dict) -> payload dict
    variants: tuple[str, ...] = ("line", "bar"),
) -> dict[str, Any]:
    """Run the ambiguous kind as an A/B contest; ARETĒ picks the winner.

    Returns the winning payload enriched with the contest ruling:
    {'ab_contest': {'variants': [...], 'winner': kind, 'excellences': {...},
    'reasoning': ...}}.
    """
    from universal_mind.arete.run_judgment import judge_run

    # A contest without data is theater: when the operator named no series,
    # the DEFAULT real series rides every variant (the same one the default
    # line chart draws) — both variants draw REAL data, the contest is real.
    params_with_data = dict(base_params)
    if not params_with_data.get("series") and not params_with_data.get("values"):
        try:
            from universal_mind.data_suite import DataSuite

            params_with_data["series"] = {"داده": list(DataSuite.DEFAULT_SERIES)}
        except Exception:  # noqa: BLE001 — the default series is a courtesy
            pass

    results: dict[str, dict[str, Any]] = {}
    excellences: dict[str, float] = {}
    vparams_made: dict[str, dict[str, Any]] = {}
    for kind in variants:
        vparams = {**params_with_data, "operation": kind}
        # series/categories stay the same across variants — same data, real contest
        if kind == "bar" and params_with_data.get("series") and not params_with_data.get("values"):
            series: list[float] = list(next(iter(params_with_data["series"].values()), []))
            vparams["values"] = list(series)
            vparams.setdefault("categories", ["الف", "ب", "ج", "د", "د"][:len(series)])
            vparams.pop("series", None)
        vparams_made[kind] = vparams
        try:
            payload = run_variant(vparams) or {}
        except Exception as exc:  # noqa: BLE001 — a failed variant is a data point
            payload = {"ok": False, "errors": {kind: str(exc)[:120]}}
        # the variant's route (chart) rides for ARETĒ's virtue scores
        payload.setdefault("route", ["chart"])
        payload.setdefault("durations_ms", {})
        results[kind] = payload
        try:
            excellences[kind] = float(judge_run(payload).get("excellence") or 0.0)
        except Exception:  # noqa: BLE001 — the judge is a lens
            excellences[kind] = 0.0

    winner = max(excellences, key=lambda k: excellences[k])
    margin = round(excellences[winner] - min(excellences.values()), 4)
    if margin <= 1e-9:
        # ARETĒ tied — the REAL second criterion: which variant renders the
        # operator's data MORE faithfully (fewer synthetic labels). A bar with
        # invented category names (الف/ب/ج) replaces real data with fiction;
        # a line carries the series verbatim. Fabrication loses.
        def _synthetic_count(kind: str) -> int:
            # the shipped params that made it — synthetic categories/pie labels
            made = vparams_made.get(kind) or {}
            n = 0
            if kind in ("bar", "barh") and made.get("categories") and not made.get("_real_categories"):
                n += len(made["categories"])
            if kind == "pie" and made.get("labels"):
                n += len(made["labels"])
            return n

        synth = {k: _synthetic_count(k) for k in variants}
        lo = min(synth.values())
        clean = [k for k in variants if synth[k] == lo]
        if len(clean) == 1:
            winner_kind = clean[0]
            reasoning = (
                f"مسابقهی A/B: «{winner_kind}» برنده شد — دادهی اپراتور را بیواسطه نشان میدهد "
                f"(واریانت دیگر {synth[[k for k in variants if synth[k] != lo][0]]} برچسبِ ساختگی میسازد)"
            )
        else:
            winner_kind = variants[0]
            reasoning = f"داوری نتوانست جدا کند — تساوی ({'، '.join(variants)})؛ {variants[0]} پیشفرض ماند"
    else:
        winner_kind = winner
        # R61-S6 — the margin is PERSIAN: a Latin 0.75 in a Persian report
        # is a digit leak (review finding 13).
        _fa_d = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        reasoning = (
            f"مسابقهی A/B: «{winner_kind}» با برتری "
            f"{f'{margin:.2f}'.translate(_fa_d)} برنده شد"
        )

    shipped = dict(results[winner_kind])
    shipped["ab_contest"] = {
        "variants": list(variants),
        "winner": winner_kind,
        "excellences": {k: round(v, 4) for k, v in excellences.items()},
        "reasoning": reasoning,
    }
    shipped["ok"] = results[winner_kind].get("ok") is True
    return shipped


def persian_ab_note(ab: dict[str, Any] | None) -> str | None:
    """The Persian voice of the A/B ruling, for the report."""
    if not isinstance(ab, dict):
        return None
    return str(ab.get("reasoning") or "") or None


def record_kind_lesson(kind: str, won: bool) -> None:
    """A won kind is a lesson — the advisor's next silent pick is sharper."""
    try:
        from universal_mind.planner_learning import teach

        teach("chart", kind, 0.9 if won else 0.5, True)
    except Exception:  # noqa: BLE001 — teaching is a bonus
        pass


__all__ = ["kind_ambiguity", "run_ab", "persian_ab_note", "record_kind_lesson"]
