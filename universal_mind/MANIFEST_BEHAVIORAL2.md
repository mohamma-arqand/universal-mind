# MANIFEST — behavioral-bug sweep, round 2

Continuing the "absence-as-success" hunt into the remaining core modules.

- [ ] H1 memory/mnemosyne.py  — query ranking / freshness / empty-haystack edge
- [ ] H2 core/executive.py    — throttle/retry count semantics, mixed state
- [ ] H3 io/gateway.py        — retry budget / failover / empty-provider edge
- [ ] H4 arete/lineage.py     — excellence fallback on missing contender card
- [ ] H5 powers/intent.py     — translation empty / non-actionable edge

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.