# MANIFEST — behavioral-bug sweep, round 3

Final suspicious surfaces not yet deep-audited.

- [x] I1 dashboard.py         — std-depth render keyed off depth-truthiness (0 showed 'awaiting') → keyed off name
- [x] I2 synthesis.py         — audited: no-specialist & no-output & composer-None branches all correct; duplicate concat lines are cosmetic
- [x] I3 demo.py              — audited: clean end-to-end, no logic bug
- [x] I4 observability/metrics.py — audited: counts/error_rate denominator correct; last_activity lexicographic OK (single timezone)

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.