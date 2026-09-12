# MANIFEST — Unify the three inconsistent "layering" sources of truth

Real architectural debt found by auditing (NOT coverage): the project has THREE
mutually-inconsistent representations of its own layer model, and the one that
actually enforces at runtime is subtly wrong against the canonical one.

## The three sources
1. `layers.py` — canonical 7-layer model: `Layer` enum, `LayerContract.may_call`
   (the authoritative "who may call whom"), `assert_call_allowed`, `@layered`.
   -> ZERO runtime enforcement, ZERO production callers (dead doc).
2. `gates/layering.py` — the runtime LayeringGate. Uses its OWN `LAYER_RANKING`
   dict (string keys) + `get_layer`/`is_foundation` + a dataclass `LayerViolation`
   (NOT an exception). Its "caller_layer > target_layer => DENY" rule is a
   one-dimensional approximation that does NOT match `LayerContract.may_call`.
3. A second `LayerViolation` in `layers.py` (a real `UniversalMindError`) that
   conflicts with the dataclass one in `gates/layering.py`.

Net effect: the layer law is (a) not enforced anywhere in production, and (b)
the only place that tries (the gate) enforces a *different* law than the
canonical model. This is exactly the class of hidden defect the user asked for.

## Plan (resumable, each step green-gated + committed)
- [x] U1 Factoring: gates/layering.py now derives ranking from the canonical
      layers.py Layer enum + LayerContract.may_call; deleted the duplicated string
      dict and the dataclass LayerViolation (re-exported the real one).
- [x] U2 Wire the gate to LayerContract.may_call via call_allowed() — the old
      "caller_layer > target_layer => DENY" was INVERTED (refused legal downward
      calls, allowed illegal upward ones). Fixed to the true direction.
- [x] U3 Prove LIVE: test_layering_live.py drives the real PrecedencePipeline —
      ARETE→MOUTH DENY, MOUTH→ARETE ALLOW.
- [x] U4 READY: 720 tests pass, mypy 0, ruff clean, READY.

## Success = one source of truth, live-enforced, matching the charter.