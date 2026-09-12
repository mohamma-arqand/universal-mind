# MANIFEST — behavioral-bug sweep, round 5 (deep)

Next layer: execution / adapters / judgment internals.

- [ ] K1 core/executive.py   — fallback/fault path, throttle, verdict round-trip (leftover)
- [ ] K2 io/adapters.py      — tool registration identity, duplicate/param edge
- [ ] K3 powers/judgment.py  — CandidateOutput scoring, virtue-miss edge, Verdict identity

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.