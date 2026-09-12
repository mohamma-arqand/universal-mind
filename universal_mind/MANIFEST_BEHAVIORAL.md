# MANIFEST — behavioral-bug sweep (the "absence-as-success" family)

A distinct bug family was found: code that mistakes "no data / no rival /
exceptional state" for a DECISIVE result (reports confidence/aligned/necessary/
converged when it should report "cannot judge"). Fixed so far: cross_judge,
red_team, causal, hypotheses, load_harness, layering (inverted), standard.rollback,
induction.matched.

Remaining suspicious modules, in order:
- [x] G1 arete/goal_drift.py      — empty-goal reported drift=False (on-course) → now drift=True
- [x] G2 arete/arbiter.py         — audited: validate (incl. duplicate id), tie, scorer interop all correct
- [x] G3 feedback/consent.py      — audited: deny-by-default + finalized=PROMOTED∧CONSENT correct
- [x] G4 memory/episodic.py       — empty-context matched every episode → now returns nothing
- [x] G5 arete/uncertainty.py     — audited: conflicts>weight>known ordering correct

Success = each real bug fixed + locked by a test; mypy 0; ruff clean; READY.