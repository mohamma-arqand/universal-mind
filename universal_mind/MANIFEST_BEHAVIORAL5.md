# MANIFEST — behavioral-bug sweep, round 5 (deep)

Next layer: execution / adapters / judgment internals.

- [x] K1 core/executive.py   — FIXED: multi-dossier no-match fell back to dossiers[0] → now raises; single-capability still general fallback
- [x] K2 io/adapters.py      — FIXED: resolve_organ 'or organs' returned unrelated organ on no domain match → now None
- [x] K3 powers/judgment.py  — FIXED: blank criterion substring-matched everything → 1.0 → false ALLOW; now skipped/all-blank defers

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.