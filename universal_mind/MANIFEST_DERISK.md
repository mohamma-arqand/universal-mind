# MANIFEST — De-risking: no new functions, fewer real bugs

User's standing directive (unchanged): private project, but more **advanced and
bug-free**. The honest path to "no bugs" is not more features — it is *finding
and removing real defects*, starting with what measurement just revealed.

## Diagnosis (measured, not guessed — coverage report + cross-reference)
1. `demiurge/strategies.py`  47%  — Parallel/Speculative/Sequential have ZERO
   production callers; only `StrategyResult` is used (by synthesis.py). Dead code
   with a real latent bug (SpeculativeStrategy IndexError on empty strategies).
2. `powers/accretion.py` 52% / `powers/hand.py` 57% / `powers/devour.py` 58% —
   three **superseded** powers. Each has a live, tested replacement:
   accretion → rubric_learning+lineage; hand → io/real_tools (91%)+commit;
   devour → pantheon/registry + io/gateway. Zero import refs outside
   `powers/__init__.py`, zero tests, zero doc refs. Dead parallel code.
3. `powers/judgment.py` 62% — **LIVE and vital** (10 production importers), but
   under-tested. This is the real gap: core logic with unfinished coverage.

## Plan (each step = one commit, resumable, green-gated)
- [x] S1 Remove dead async strategies (`demiurge/strategies.py`), keep the one
      live type `StrategyResult` (relocate to synthesis.py).  (fixes latent bug)
- [x] S2 Remove superseded powers `accretion`/`hand`/`devour` (+ dead `__init__`
      exports). Replaces half-tested logic with already-tested alternatives.
- [x] S3 Close the *real* gap: raise `powers/judgment.py` coverage (62% → 100%),
      fixed a latent ZeroDivisionError on empty criteria.
- [x] S4 Re-verify the whole system is green after surgery: mypy 0, ruff clean,
      41 probes READY, 547 tests pass, dead modules confirmed gone, total
      coverage 91% → 96%.

## Success = measurable
- Dead modules gone; imports clean; `__init__` no longer exports ghosts.
- `judgment.py` coverage up; total tests still pass; mypy 0; READY stamp.
- Latent SpeculativeStrategy bug eliminated (module removed).