"""Tests: R39 — the empty band, the unknown band, and honest recovery.

«» gets a warm hand-off (never a silent hole); an unrecognized command
carries the NEAREST real capability words, so a typo is one step from
recovery instead of a dead end.
"""

from __future__ import annotations

from universal_mind.persian_router import route_and_run
from universal_mind.spelling_recovery import suggest_for


# ---------- L1: the empty band ----------
def test_empty_command_gets_a_warm_handoff() -> None:
    p = route_and_run("")
    assert p["ok"] is False
    assert p.get("agent_report"), "never a silent hole"
    assert "ننوشتی" in p["agent_report"]


def test_whitespace_only_is_the_empty_band() -> None:
    p = route_and_run("   ")
    assert p["ok"] is False
    assert p.get("agent_report")


# ---------- L2: the unknown band carries suggestions ----------
def test_unknown_command_carries_suggestions() -> None:
    p = route_and_run("سنجاق کن نقشه را")
    assert p["ok"] is False
    assert p.get("suggestions"), "failure must point somewhere"
    # suggestions are REAL capability words (never a bare filler like «کن»)
    assert all(len(s) >= 3 for s in p["suggestions"])


def test_nonsense_still_offers_something() -> None:
    p = route_and_run("چرت و پرت زدن روی زمین")
    assert p["ok"] is False
    assert p.get("agent_report")


def test_suggest_for_is_bounded() -> None:
    # close token -> near words
    assert suggest_for("نقشه")
    # nothing Persian at all -> honest empty
    assert suggest_for("zzqx qwerty") == []


def test_suggestions_never_contain_fillers() -> None:
    for token in ("سنجاق", "نقشه", "آمارگیری"):
        for s in suggest_for(token):
            assert s not in {"کن", "کنید", "را", "و", "در"}


# ---------- regression: recognized commands unchanged ----------
def test_recognized_command_not_harmed() -> None:
    p = route_and_run("میانگین ۵ و ۷ را حساب کن")
    assert p["ok"] is True
    assert p["route"] == ["data"]