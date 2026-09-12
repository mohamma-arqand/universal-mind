# MANIFEST — Sweep 2: drive every live module < 95% toward 100%

Continuation of the coverage-to-bug-fix method. Remaining live modules under
95% (some already high but unfinished):

Priority = (uncovered lines × bug-likelihood). Most impactful first.

- [x] X1 gates/layering.py        (87%→100%, 9 cases) — FIXED dead downward-command
      enforcement + Flaky HTTP test root cause (socket→transient retry).
- [x] X2 core/errors.py           (92%→100%, 5 cases) — get_fallback/recovery/
      retry-exhaustion; hardened max_retries=0.
- [x] X3 io/real_tools.py         (91%→100%, 6 cases) — url/health/404/unknown-op.
- [x] X4 io/adapters.py           (93%→100%, 9 cases) — secret-env/shell/mcp.
- [x] X5 powers/generator.py      (90%→99%, 6 cases) — expected/load/benchmark.
- [x] X6 io/gateway.py            (90%→98%, 13 cases) — 5xx/429/malformed/scripted.
- [x] X7 arete/virtue.py          (87%→97%, +FIX AttributeError on unknown gate).
- [x] X8 powers/power_zero.py     (88%→98%) — immutability + minting.
- [x] X9 io/stub_server.py        (90%→98%, 11 cases total w/ mnemosyne).
- [x] X10 memory/mnemosyne.py     (90%→98%) — recall/decay/clamp branches.
- [x] X11 end-to-end multi-layer test (test_end_to_end_multilayer.py) — one intent
      through MOUTH→executive→judgment→durable→self-awareness, all auditable.

## Success = each module coverage up, real bugs fixed, mypy 0, READY.