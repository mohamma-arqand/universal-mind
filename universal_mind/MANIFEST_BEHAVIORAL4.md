# MANIFEST — behavioral-bug sweep, round 4 (deep)

Deeper audit of judgment/self/temporal modules only surface-read so far.

- [x] J1 core/metacognition.py      — audited: 3-axes count + robust-special all correct; no empty-input mispricing (all-None → SKEPTICAL)
- [x] J2 core/temporal_awareness.py — audited: naive→UTC assumption consistent; freshness=max(0,…) defensive; no empty-trace edge
- [x] J3 arete/lineage.py           — FIXED: 'deferred' was not counted as a losing branch (only 'rejected'); deferred near-misses were buried

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.