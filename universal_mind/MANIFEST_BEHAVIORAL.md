# MANIFEST — behavioral-bug sweep (the "absence-as-success" family)

A distinct bug family was found: code that mistakes "no data / no rival /
exceptional state" for a DECISIVE result (reports confidence/aligned/necessary/
converged when it should report "cannot judge"). Fixed so far: cross_judge,
red_team, causal, hypotheses, load_harness, layering (inverted), standard.rollback,
induction.matched.

Remaining suspicious modules, in order:
- [ ] G1 arete/goal_drift.py      — empty-goal reported drift=False (cannot-judge vs on-course)
- [ ] G2 arete/arbiter.py         — tie/accept threshold edge cases, mixed is-vs-==
- [ ] G3 feedback/consent.py      — verdict aggregation / threshold direction
- [ ] G4 memory/episodic.py       — empty-context match-all + created_at sort assumptions
- [ ] G5 arete/uncertainty.py     — UNKNOWN vs empty-observation distinction

Success = each real bug fixed + locked by a test; mypy 0; ruff clean; READY.