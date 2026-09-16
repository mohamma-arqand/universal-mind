"""Persian natural-language router — فارسی بگو، سیستم خودش اجرا کند.

The bridge between a Persian-speaking operator and the 87-operation super-platform:
a command like «میانگین این اعداد را حساب کن و نمودارش کن» is mapped to the
capability chain (data → chart) and executed through the same orchestrate engine
every other door uses.

This is a deterministic keyword router over declared vocabulary — NOT an LLM. Every
mapping is explicit and testable: a given Persian phrase always routes to the same
chain. Unknown words are reported honestly (never a guessed chain).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from universal_mind.tool_registry import ToolRegistry


@dataclass(frozen=True)
class PersianRoute:
    """The learned/derived plan for one Persian command."""

    command: str
    capabilities: tuple[str, ...]   # execution order
    matched_words: tuple[str, ...]  # which Persian words triggered each capability
    unknown: tuple[str, ...]        # Persian words that matched nothing (honest)

    @property
    def ok(self) -> bool:
        return bool(self.capabilities)


# Persian vocabulary → capability. One phrase can trigger several capabilities
# (e.g. «نمودار» → chart, «ذخیره» → database), and chains are built from what fires.
_VOCAB: tuple[tuple[str, str], ...] = (
    # data (numpy) — formal AND colloquial forms
    ("میانگین", "data"),
    ("میانگینشو", "data"),
    ("میانگینش", "data"),
    ("میانگین بگیر", "data"),
    ("میانگین بگیره", "data"),
    ("حسابش کن", "data"),
    ("حساب کن", "data"),
    ("میانگین ", "data"),
    ("انحراف", "data"),
    ("آمار", "data"),
    ("محاسبه", "data"),
    ("همبستگی", "data"),
    ("معادله", "data"),
    ("درصد", "data"),
    ("نرمال", "data"),
    ("ماتریس", "data"),
    # chart (matplotlib) — formal AND colloquial
    ("نمودار", "chart"),
    ("نمودارشو", "chart"),
    ("نمودارش", "chart"),
    ("نمودار بکش", "chart"),
    ("بکش", "chart"),
    ("رسم", "chart"),
    ("رسمش کن", "chart"),
    ("خطی", "chart"),
    ("میله", "chart"),
    ("دایره", "chart"),
    ("هیستوگرام", "chart"),
    ("پراکنده", "chart"),
    # pdf (reportlab)
    ("پی دی اف", "pdf"),
    ("پی‌دی‌اف", "pdf"),
    ("گزارش", "pdf"),
    ("سند", "pdf"),
    ("فاکتور", "pdf"),
    ("جدول در سند", "pdf"),
    # image (Pillow)
    ("تصویر", "image"),
    ("عکس", "image"),
    ("تغییر اندازه", "image"),
    ("برش", "image"),
    ("چرخش", "image"),
    ("فیلتر تصویر", "image"),
    ("سیاه سفید", "image"),
    ("واترمارک", "image"),
    # database (SQLite) — formal AND colloquial
    ("ذخیره", "database"),
    ("ذخیرهش کن", "database"),
    ("ذخیره کن", "database"),
    ("دیتابیس", "database"),
    ("جدول", "database"),
    ("کوئری", "database"),
    ("پرس‌وجو", "database"),
    # media (ffmpeg)
    ("ویدیو", "media"),
    ("فریم", "media"),
    ("تبدیل ویدیو", "media"),
    # archive (gzip)
    ("فشرده", "archive"),
    ("آرشیو", "archive"),
    ("زیپ", "archive"),
    # vision (OpenCV) — تحلیل تصویر واقعی
    ("بینایی", "vision"),
    ("تحلیل تصویر", "vision"),
    ("لبه", "vision"),
    ("لبهها", "vision"),
    ("کنتور", "vision"),
    ("خطوط تصویر", "vision"),
    ("تشخیص لبه", "vision"),
    ("پردازش تصویر", "vision"),
    # ai (sklearn/scipy) — یادگیری ماشین واقعی
    ("یادگیری", "ai"),
    ("یادگیری ماشین", "ai"),
    ("خوشه", "ai"),
    ("خوشهبندی", "ai"),
    ("خوشه بندی", "ai"),
    ("طبقهبندی", "ai"),
    ("طبقه بندی", "ai"),
    ("رگرسیون", "ai"),
    ("مدل", "ai"),
    ("آموزش", "ai"),
    ("فوریه", "ai"),
    ("سیگنال", "ai"),
    ("پیشبینی", "ai"),
    ("پیش بینی", "ai"),
    # saved chains — «زنجیرهی X را اجرا کن» runs the operator's saved chain
    ("زنجیره", "chain"),
    ("زنجیرهی", "chain"),
    # compute (node)
    ("جاوااسکریپت", "compute"),
    ("جاوا اسکریپت", "compute"),
    ("نود", "compute"),
    # notify (Windows toast)
    ("اطلاع بده", "notify"),
    ("اعلان", "notify"),
    ("پیام بده", "notify"),
    ("یادآوری کن", "notify"),
    # clipboard
    ("کلیپبورد", "clipboard"),
    ("کپی کن", "clipboard"),
    ("بفرست به کلیپبورد", "clipboard"),
)

# Ordering preference: which capability should run FIRST when several fire.
# data/compute produce inputs; chart/pdf consume them; database/notify/archive
# are sinks. The order below is the natural data-flow order.
_PRIORITY: tuple[str, ...] = (
    "data", "compute", "image", "media", "vision", "ai",
    "chart", "pdf", "database", "archive", "clipboard", "notify",
)
# "chain" is a dispatch word, never an executable capability: when other words
# also fire, the chain pseudo-capability is dropped so the real ones run.
_NON_EXECUTABLE = {"chain"}


def _resolve_saved_chain(command: str) -> tuple[str, ...] | None:
    """Find the operator's saved chain whose name appears in the command.

    «زنجیرهی گزارش هفتگی را اجرا کن» matches a saved chain named «گزارش هفتگی».
    Returns the chain's capabilities, or None when no saved chain name matches —
    never a guessed chain.
    """
    try:
        from universal_mind.chains_store import ChainsStore
    except Exception:  # noqa: BLE001 — a missing store never breaks routing
        return None
    try:
        saved = ChainsStore().load()
    except Exception:  # noqa: BLE001
        return None
    lowered = command.lower()
    # Longest name first, so a longer saved name wins over a shorter prefix.
    for chain in sorted(saved, key=lambda c: -len(c.name)):
        if chain.name in lowered:
            return chain.capabilities
    return None


def route(command: str) -> PersianRoute:
    """Map a Persian command to a capability chain (deterministic, honest)."""
    lowered = command.lower()
    matched: dict[str, list[str]] = {}

    for word, capability in _VOCAB:
        if word in lowered:
            matched.setdefault(capability, []).append(word)

    if "chain" in matched and not any(c for c in matched if c != "chain"):
        # A pure chain command («زنجیرهی X را اجرا کن») — the route is resolved
        # from the operator's SAVED chains, not from the capability vocabulary.
        saved = _resolve_saved_chain(command)
        if saved is not None:
            return PersianRoute(
                command=command,
                capabilities=saved,
                matched_words=("زنجیره",),
                unknown=(),
            )
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))

    if not matched:
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))

    # Order capabilities by the natural data-flow priority; ties keep first-seen.
    executable = [c for c in matched if c not in _NON_EXECUTABLE]
    if not executable:
        # A pure «زنجیره...» command (handled above) or nothing executable.
        return PersianRoute(command=command, capabilities=(), matched_words=(), unknown=(lowered,))
    caps = sorted(
        executable,
        key=lambda c: (_PRIORITY.index(c) if c in _PRIORITY else len(_PRIORITY), executable.index(c)),
    )
    words = tuple(w for c in caps for w in matched[c])

    # Honest unknowns: Persian words present in the command that matched nothing.
    import re

    tokens = [w for w in re.split(r"[\s،.,؛!؟]+", command) if w.strip()]
    known_flat = {w for w, _ in _VOCAB}
    unknown: list[str] = [t for t in tokens if t not in known_flat and not t.replace(".", "").isdigit()]

    return PersianRoute(
        command=command,
        capabilities=tuple(caps),
        matched_words=words,
        unknown=tuple(unknown),
    )


def route_and_run(
    command: str,
    registry: ToolRegistry | None = None,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route a Persian command AND execute the resulting chain for real.

    Returns a JSON-ready payload: the route (capabilities, matched words) plus the
    real per-capability results from orchestrate. A command that matches nothing
    returns ok=False with the honest reason — never a fabricated chain.
    """
    from universal_mind.orchestration import orchestrate
    from universal_mind.persian_params import extract_params
    from universal_mind.real_tool_registry import (
        real_connector_factory,
    )
    from universal_mind.tool_registry import (
        ConnectionMechanism,
        ToolConnectionSpec,
        ToolEntry,
    )
    from universal_mind.tool_registry import (
        ToolRegistry as _Registry,
    )

    route_result = route(command)
    if not route_result.ok:
        return {
            "ok": False,
            "command": command,
            "error": "هیچ قابلیتی شناخته نشد",
            "unknown": list(route_result.unknown),
        }

    caps = list(route_result.capabilities)
    reg = registry if registry is not None else _Registry()
    for cap in caps:
        reg.register(
            ToolEntry(
                name=f"fa-{cap}",
                capability=cap,
                connection=ToolConnectionSpec(mechanism=ConnectionMechanism.SUBPROCESS, command="unused"),
                absorbable=True,
            )
        )

    # Real parameters extracted FROM the command itself: «میانگین ۲ و ۴» must
    # compute [2, 4], not a default series. A capability receives only the params
    # its contract accepts (the dispatch constrains what it is given).
    capability_params = params or {cap: extract_params(command, cap) for cap in caps}

    syn = orchestrate(
        reg,
        caps,
        connector_factory=real_connector_factory,
        capability_params=capability_params,
    )
    # Record the real run to the persistent history (the advisor learns from it).
    try:
        from universal_mind.run_history import RunHistory

        RunHistory().record(command, caps, syn.ok)
    except Exception as exc:  # noqa: BLE001 — a failed history write never breaks the run
        import sys

        print(f"[history] ثبت اجرا ناموفق بود: {exc}", file=sys.stderr)
    return {
        "ok": syn.ok,
        "command": command,
        "route": caps,
        "matched_words": list(route_result.matched_words),
        "unknown": list(route_result.unknown),
        "extracted_params": capability_params,
        "result": syn.output["synthesized_from"],
        "errors": {s.capability: s.error for s in syn.sub_outputs if not s.ok},
        "durations_ms": {s.capability: round(s.duration_ms, 3) for s in syn.sub_outputs},
        "_registry": reg,  # kept internal: the caller may reuse the registry
    }


__all__ = ["PersianRoute", "route", "route_and_run"]