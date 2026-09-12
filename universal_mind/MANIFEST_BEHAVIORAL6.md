# MANIFEST — behavioral-bug sweep, round 6 (remaining modules)

Sweep the highest-risk modules not yet deep-audited in rounds 1-5.

- [x] L1 demiurge/decompose.py   — audited: split heuristic + depends_on chain correct; case-inconsistency (single-goal keeps case, split lowercases) is cosmetic
- [x] L2 prometheus/proposer.py  — audited: three thresholds + failures-only REORDER gate all correct
- [x] L3 pantheon/budget.py      — audited: _candidates_for correctly refuses fall-to-everything (mirrors the adapters fix)
- [x] L4 memory/lifespan.py      — audited: aware-clock arithmetic, horizon filter, significance-ranked decay all correct
- [x] L5 arete/counterfactual.py — FIXED: reported original/reversed from scorecard (back-fills 0.0) not the candidate's declared virtues → now reads the actual flipped premise
- [x] L6 mouth/commit.py         — audited: empty/vague/conflict gates, caution bar threshold all correct

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.