# MANIFEST — behavioral-bug sweep, round 6 (remaining modules)

Sweep the highest-risk modules not yet deep-audited in rounds 1-5.

- [ ] L1 demiurge/decompose.py   — sub-intent split edge, empty-goal decomposition
- [ ] L2 prometheus/proposer.py  — proposal ranking, empty-population edge
- [ ] L3 pantheon/budget.py      — allocation math, zero-budget edge
- [ ] L4 memory/lifespan.py      — recall-context boundary, empty-history edge
- [ ] L5 arete/counterfactual.py — robustness direction, no-alternative edge
- [ ] L6 mouth/commit.py         — structured-intent fallback, empty utterance edge

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.