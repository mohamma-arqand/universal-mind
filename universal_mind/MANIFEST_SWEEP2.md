# MANIFEST — Sweep 2: drive every live module < 95% toward 100%

Continuation of the coverage-to-bug-fix method. Remaining live modules under
95% (some already high but unfinished):

Priority = (uncovered lines × bug-likelihood). Most impactful first.

- [ ] X1 gates/layering.py        (87%,  8 lines) — layer enforcement, safety-critical
- [ ] X2 core/errors.py           (92%,  6 lines) — retry/backoff/fallback helpers
- [ ] X3 io/real_tools.py         (91%,  8 lines) — fail-safe real tool execution
- [ ] X4 io/adapters.py           (93%,  8 lines) — provider adapters
- [ ] X5 powers/generator.py      (90%,  9 lines) — insight-driven generation
- [ ] X6 io/gateway.py            (90%, 17 lines) — provider routing (largest io gap)
- [ ] X7 arete/virtue.py          (87%,  5 lines) — virtue weighting
- [ ] X8 powers/power_zero.py     (88%,  7 lines) — absolute veto
- [ ] X9 io/stub_server.py        (90%, 11 lines) — offline stub HTTP
- [ ] X10 memory/mnemosyne.py     (90%, 12 lines) — durable memory lifecycle

Then: end-to-end multi-layer scenarios (X11).

## Success = each module coverage up, real bugs fixed, mypy 0, READY.