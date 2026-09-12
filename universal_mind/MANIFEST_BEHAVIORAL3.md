# MANIFEST — behavioral-bug sweep, round 3

Final suspicious surfaces not yet deep-audited.

- [ ] I1 dashboard.py         — real-data rendering / division / empty-store edges
- [ ] I2 synthesis.py         — result fusion / empty specialist / evidence edges
- [ ] I3 demo.py              — registration idempotency warning / echo path
- [ ] I4 observability/metrics.py — error_rate denominator / empty-ledger edges

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.