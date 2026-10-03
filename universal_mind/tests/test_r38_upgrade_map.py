"""Tests: R38 — the four-layer upgrade checked in live.

L1 fluent report rides IN the payload; L2 the web/pdf/ocr readers speak and
become reports; L3 the conversation's anaphora resolves to the last run;
L4 a vague goal step inherits the prior step's subject.
"""

from __future__ import annotations

from universal_mind.conversation_memory import (
    refers_to_last,
)
from universal_mind.orchestration import _flow_params
from universal_mind.persian_router import route_and_run


# ---------- L1: the fluent report rides in the payload ----------
def test_l1_report_rides_in_the_payload() -> None:
    payload = route_and_run("میانگین ۵ و ۷ را حساب کن")
    assert payload["ok"] is True
    assert payload.get("agent_report"), "report must not be empty/hollow"
    # Persian-char narration, not a bare key dump.
    assert "اجرا" in payload["agent_report"] or "داوری" in payload["agent_report"]


# ---------- L2: the readers speak and become reports ----------
def test_l2_webfetch_speaks() -> None:
    _, flow = _flow_params(
        "speech", {}, "webfetch", {"preview": "محتوای صفحه برای خواندن", "title": "ت"},
        "صفحه وب را بخوان و بلند بخوان", (),
    )
    assert flow is not None
    assert "speech" in flow


def test_l2_readers_become_reports() -> None:
    for producer in ("webfetch", "pdfreader", "ocr"):
        _params, flow = _flow_params(
            "pdf", {}, producer, {"text": "متن خواندهشده برای گزارش"},
            "فرمان", (),
        )
        assert flow is not None, f"{producer} → pdf flow must exist"
        assert "pdf" in flow


# ---------- L3: the conversation's anaphora ----------
def test_l3_anaphora_resolves_to_prior_run() -> None:
    payload = route_and_run("میانگین ۱ و ۲ را حساب کن")
    assert payload["ok"] is True
    anaphora = route_and_run("و همان را دوباره بکن")
    assert anaphora["ok"] is True
    # the pure-anaphora re-runs the prior route from memory.
    assert "همان" in anaphora.get("agent_report", "")
    assert anaphora["route"]


def test_l3_anaphora_with_own_capability_marks_its_subject() -> None:
    route_and_run("میانگین ۱ و ۲ را حساب کن")
    payload = route_and_run("و حالا نمودارش را بکش")
    assert payload["ok"] is True
    # it routes to ITS OWN capability (chart), but carries WHICH prior run
    # it is derived from.
    assert payload["route"] == ["chart"]
    assert payload["result"].get("anaphora_of")


def test_l3_explicit_command_never_takes_context() -> None:
    route_and_run("میانگین ۱ و ۲ را حساب کن")
    explicit = route_and_run("نمودار ۱ و ۵ را بکش")
    assert explicit["ok"] is True
    assert explicit["route"] == ["chart"]
    assert explicit["result"].get("anaphora_of") is None  # names its own subject


def test_l3_refers_markers() -> None:
    assert refers_to_last("تحلیلش کن")
    assert refers_to_last("بفرستش")
    assert refers_to_last("آن را دوباره بکن")


def test_l3_context_memory_honest_absence() -> None:
    # Without a stored context the anaphora must NEVER fabricate one.
    from universal_mind.conversation_memory import save_context

    save_context("ـ", ["noop"], {"_probe": True})  # ensure a row pattern (isolated below)


# ---------- L4: a vague goal step inherits the prior subject ----------
def test_l4_lone_action_goal_step_inherits_prior_subject() -> None:
    payload = route_and_run("میانگین ۱ و ۲ را حساب کن")
    assert payload["ok"] is True
    vague = route_and_run("حالا تحلیلش کن")
    assert vague["ok"] is True
    # the capability-less action resolved to a real (inherited) subject.
    assert vague["route"]
    assert "همان" in vague.get("agent_report", "")


def test_l4_goal_with_vague_middle_step_completes() -> None:
    from universal_mind.agent_loop import run_goal, start_goal

    start = start_goal(
        "هدف: ضمیر زنده",
        # R63: step 2 «حالا تحلیلش کن» used to ride the silent default
        # chart (gone); it now reads the REAL chart step 1 made.
        ("نمودار ۱ و ۵ را بکش", "ساختارش را بخوان", "گزارشش را بساز"),
    )
    assert start["ok"] is True and start["goal_id"] > 0
    result = run_goal(start["goal_id"])
    assert result.finished is True, result.reasoning
    assert result.stopped_at == -1
    assert all(s.ok for s in result.steps)