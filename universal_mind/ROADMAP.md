# ROADMAP — Universal Mind → Beyond-World-Class

The honest theory of "beyond world class": it is not a destination but a path,
and that path follows one law — *any system that only measures itself hits its
own ceiling.* Every strengthening below is therefore wired to an external
reference, not just self-assessment.

Three phases, each one measurable beat at a time. Each work item:
**commit (green) → unit tests → probe → real execution evidence.** No half-built
slabs; no code bloat. A system that does four things completely beats a system
that does twenty-four things half-way.

---

## Phase 1 — Deeper (Cognition): multi-hypothesis, uncertainty, counterfactual

Root cause of "multi-faceted" and "infinitely intelligent": the mind must reason
over *hypotheses* and *doubt*, not lock into its first guess.

- [x] 1.1 Counterfactual reasoning — "would this still hold if X were false?"  (arete/counterfactual.py)
- [x] 1.2 Hypothesis ensemble — hold several readings of an intent, converge on evidence  (demiurge/hypotheses.py)
- [x] 1.3 Causal reasoning — "why this outcome" + "what would change it"  (demiurge/causal.py)
- [x] 1.4 Temporal episodic memory — recall *when* and *in what context*, not just *what*  (memory/episodic.py)
- [x] 1.5 Inductive generalization — learn a rule from few examples, apply to unseen  (demiurge/induction.py)
- [x] 1.6 Epistemic uncertainty — a real `UNKNOWN` verdict with a reason, not a guess  (arete/uncertainty.py)

## Phase 2 — More self-governing (Governance): provable, drift-aware, rubric-learning

- [x] 2.1 Cross-model judge — a second/foreign model judging the judge (anti-alignment)  (arete/cross_judge.py)
- [x] 2.2 Goal-drift detection — notice when the path diverged from the original goal  (arete/goal_drift.py)
- [x] 2.3 Continuous self-code-audit — like G4, but automatic and periodic  (core/self_code_audit.py)
- [ ] 2.4 Rubric learning — the evaluation rubric improves from its own mistakes
- [ ] 2.5 Red-team/blue-team — attack + defend continuously (auto security test)
- [ ] 2.6 Provable policy — audit every allow/deny as a verifiable reason chain

## Phase 3 — More connected (World): multilingual, temporal, real tools

- [ ] 3.1 Real multilingual understanding — language-independent intent layer
- [ ] 3.2 Temporal/environment awareness — clock, zone, "what time is it and what it means"
- [ ] 3.3 Real external tools — a real service behind the gateway, fail-safe
- [ ] 3.4 Distributed memory — several instances share one synchronized ledger
- [ ] 3.5 Cross-session identity — continuous identity survives restart
- [ ] 3.6 Observable deploy — real metrics (prometheus/otel), not just unit tests

---

## Governance of this roadmap

- Finished work is marked `[x]` with the commit that delivered it.
- The order is deliberate: Phase 1 (deeper) before Phase 2 (governing) before
  Phase 3 (connected), because a mind that reasons deeply and governs itself can
  safely grow outward; outward growth without depth is just surface area.
- Every phase ends with a full `verify.py` READY gate before the next begins.