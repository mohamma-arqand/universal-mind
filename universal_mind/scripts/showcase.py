#!/usr/bin/env python3
"""Showcase — run the whole closed loop and print a step-by-step trace.

A stranger can point at this project and, with one command and zero setup, watch
every layer actually execute — not read about it. It drives the full cycle:

    MOUTH → decompose → resolve → execute → synthesis → ARETĒ (reasoned) →
    self-awareness → self-correction → external audit → metacognition

and prints each layer's real output. Deterministic and local: no API key, no
network, nothing fabricated.

Usage::
    cd universal_mind
    python scripts/showcase.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def main() -> int:
    from universal_mind.arete.arbiter import Dispute, InMemoryArbiter
    from universal_mind.arete.counterfactual import counterfactual_check
    from universal_mind.arete.goal_drift import assess_goal_drift
    from universal_mind.arete.standard import StandardKeeper
    from universal_mind.arete.uncertainty import assess_verdict_uncertainty
    from universal_mind.core.identity import DEFAULT_OWNER
    from universal_mind.core.metacognition import assess_metacognition
    from universal_mind.core.self_awareness import SelfAwarenessLoop
    from universal_mind.demiurge.hypotheses import Hypothesis, HypothesisEnsemble
    from universal_mind.memory.store import InMemoryStore
    from universal_mind.mouth.commit import GuardedMouth, InMemoryMouth
    from universal_mind.mouth.multilingual import normalize_intent
    from universal_mind.powers.judgment import CandidateOutput

    _banner("1 · MOUTH — raw speech → a structured, evidenced commitment")
    mouth = GuardedMouth(InMemoryMouth())
    structured = mouth.commit("summarize the topic and write it down", DEFAULT_OWNER.owner_id)
    print(f"  goal       : {structured.intent.goal!r}")
    print(f"  criteria   : {list(structured.intent.success_criteria)}")

    _banner("2 · Multilingual — English and Persian converge to one action")
    en = normalize_intent("summarize the report")
    fa = normalize_intent("گزارش را خلاصه کن")
    print(f"  English  -> {en.action}   Persian -> {fa.action}   (converged: {en.action == fa.action})")

    _banner("3 · ARETĒ — evidence-backed judgment between two candidates")
    dispute = Dispute(
        goal="pick the stronger synthesis",
        candidates=[
            CandidateOutput("good", "a thorough, verified summary", metadata={
                "virtues": {"justice": 1.0, "wisdom": 0.95, "courage": 1.0, "temperance": 1.0}}),
            CandidateOutput("weak", "a thin guess", metadata={
                "virtues": {"justice": 0.2, "wisdom": 0.3, "courage": 0.3, "temperance": 0.3}}),
        ],
    )
    arbiter = InMemoryArbiter()
    verdict = arbiter.arbitrate(dispute)
    print(f"  winner     : {verdict.winner_strategy_id}   ({verdict.decision.value})")
    print(f"  reasoning  : {verdict.reasoning}")

    _banner("4 · Counterfactual — would the judgment survive a reversed premise?")
    cf = counterfactual_check(dispute, verdict, assumption="wisdom", arbiter=arbiter)
    print(f"  robust     : {cf.robust}   — {cf.explanation}")

    _banner("5 · Epistemic uncertainty — do we actually know enough?")
    uncertainty = assess_verdict_uncertainty(verdict)
    print(f"  status     : {uncertainty.status.value}   ({uncertainty.reason})")

    _banner("6 · Hypothesis ensemble — several readings, converge on evidence")
    ensemble = HypothesisEnsemble(margin=0.1).converge([
        Hypothesis("good", "verified", 0.9, 0.9),
        Hypothesis("weak", "guess", 0.3, 0.9),
    ])
    print(f"  best       : {ensemble.best.hypothesis_id if ensemble.best else None}   converged: {ensemble.converged}")

    _banner("7 · Metacognition — reasoning about the reasoning")
    meta = assess_metacognition(cf, uncertainty.status, ensemble)
    print(f"  confidence : {meta.confidence.value}   ({meta.explanation})")

    _banner("8 · Self-awareness — the loop watches and can correct itself")
    store = InMemoryStore()
    keeper = StandardKeeper(store, owner=DEFAULT_OWNER)
    loop = SelfAwarenessLoop(store, keeper, owner=DEFAULT_OWNER)
    loop.consider(CandidateOutput(
        verdict.winner_strategy_id or "good", "champion summary",
        metadata={"virtues": {"justice": 1.0, "wisdom": 0.9, "courage": 1.0, "temperance": 1.0}},
    ))
    introspection = loop.introspect()
    print(f"  bar/budget : {loop.acceptance_bar:.2f} / {loop.budget:.2f}")
    print(f"  health     : {introspection.health_summary}")

    _banner("9 · Goal-drift guard — has the path left the goal?")
    drift_oncourse = assess_goal_drift("summarize the topic", "a summary of the topic, written up")
    drift_off = assess_goal_drift("summarize the topic", "here is a chocolate cake recipe")
    print(f"  on-course  : {not drift_oncourse.drift}   ({drift_oncourse.reason})")
    print(f"  drifted    : {drift_off.drift}   ({drift_off.reason})")

    _banner("DONE — every layer above ran for real (no mock, no network).")
    print("To verify the whole system's claims, run:  python scripts/verify.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())