# Beyond-World-Class — Four Paths, In Order

Four independent workstreams, each committing its own green slice. Resumable:
if interrupted, pick up from the first UNSET step — every prior artifact is
already committed and verified.

## G1 — Independent evaluation (second judge, not self-praise)
A self-aware mind that only self-assesses has one blind spot: it never meets a
foreign standard. Build an Independent Evaluator that audits the *judgment +
self-correction loop itself*, scoring it against an external rubric and writing
an `external_audit` ledger entry. This is the charter's "human verdict" made
systematic: evaluation from outside the loop, not from inside it.
- [ ] G1 new module + tests + probe

## G2 — Evolutionary architecture (insight → generation feedback)
The insights the mind already produces (budget cuts, bar raises, rejected
branches, best-losing-contenders) are currently dead-ends: reported, then
forgotten. Route them back into Power Zero / synthesis as *constraints* so the
next generation is shaped by the last cycle's learning — true open-ended growth,
not re-derivation.
- [ ] G2 new module + tests + probe

## G3 — Real scale & deployment (load, not just unit tests)
Unit tests prove correctness, not capacity. A synthetic load harness measures
throughput/latency of the loop under real concurrency, and a durable deploy
story (ledger persistence + restart recovery) is exercised end-to-end.
- [ ] G3 new module + tests + probe

## G4 — Foundational audit (shore up before adding)
An honest, evidence-backed pass over the current base: find the real weak
points (coverage gaps, dead paths, coupling) and fix them BEFORE building the
three features above — so G1–G3 stand on the strongest possible floor.
- [x] G4 audit report + fixes + tests  (orphaned telemetry/synergy removed + layer maps cleaned)

## Final gate
- [ ] full verify READY + consolidated status