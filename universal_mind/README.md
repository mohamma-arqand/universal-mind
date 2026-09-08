# Universal Mind

A seed-core, local-first orchestration project built around three layers:

- **Core**: identity, intent, clock, errors, and the Executive Mind.
- **Pantheon**: capability contracts and the registry of executable dossiers.
- **Memory / Mnemosyne**: append-only ledger storage and time-aware recall.
- **Feedback**: human verdicts attached to ledger records.
- **ARETĒ**: virtue-based, non-compensatory arbitration of competing candidates
  (`arete/`) — a candidate that violates a hard-gate virtue (Justice by default)
  is disqualified regardless of overall score; excellence ties rule DEFER.
  Every verdict carries a mandatory evidence bundle (`arete/evidence.py`):
  judgment is anchored to inspectable `EvidencePoint`s (a trusted source, a
  type, a citation, a weight), never to a bare score or a majority vote —
  enforcing "judgment backed by evidence".
- **Gateway** (`io/`): adapters to external providers — a `Provider` protocol,
  deterministic reference providers (Echo, Scripted), an OpenAI-compatible
  `HttpChatProvider`, and a `Gateway` that retries with backoff and fails over
  across an ordered provider list. API keys resolve lazily via a
  `SecretResolver` and are never stored or logged.
- **Prometheus** (`prometheus/`): safe, evidence-backed self-evolution. Observes
  the ledger → distills metrics → proposes evolution actions → vets them against
  a conservative policy (risk cap, reversibility requirement, min observations)
  → applies only via an explicit reversible applier. Safe by default: the
  reference engine is proposals-only. `ThrottleApplier` realizes a vetted
  `TIGHTEN_THROTTLE` proposal on the live `ExecutionThrottle` (reversible, with
  a safety floor), so self-evolution can be consequential yet never destructive.
  `prometheus/apply.py` routes each vetted proposal to the matching reversible
  applier (`evolve_and_apply`): `ThrottleApplier` tightens the throttle, a
  `FallbackOrderApplier` installs a fallback chain — all reversible.
- **Integration** (`integration.py`): the composed face that closes the loop —
  a `GatewayCapability` runs inside the ExecutiveMind, the produced output is
  arbitrated by ARETĒ against a baseline, and Prometheus watches the same
  ledger. `InMemoryIntegrationHarness` makes the whole system runnable and
  deterministic with an injected provider.
- **Durable** (`durable.py`): `PersistentMind` binds the composed runtime to an
  on-disk `LocalJSONLStore`, so the ledger survives a restart. Registration is
  idempotent across reopens (`PantheonRegistry.restore_capability`), letting a
  reopen reload the same ledger and recover recorded faults.

## Deployment

`pyproject.toml` packages the project and exposes a `universal-mind` console
script (see `universal_mind/cli.py`):

- `universal-mind health` — exercises the full stack and prints JSON status;
  exit 0 only when healthy.
- `universal-mind demo` — the reference end-to-end demo.
- `universal-mind interactive` — REPL over the composed harness (local providers).
- `universal-mind chat` — REPL wired to a real OpenAI-compatible provider
  (base URL/model/key read from `UM_OPENAI_BASE_URL`, `UM_OPENAI_MODEL`,
  `UM_OPENAI_API_KEY`; fail-safe without a key).
- `universal-mind replay --dir <dir>` — recover + audit an on-disk ledger
  (JSON summary of record kinds and counts).
- `universal-mind evolve --dir <dir>` — run one Prometheus self-evolution pass
  over an on-disk ledger (proposals, applied, throttle threshold as JSON).
- `universal-mind --version` — the package version.

The deployment shape is a plain, venv-installable package — no container
runtime is required (the project is deliberately Docker-free). `pip install .`
from the repo root provides the `universal-mind` console script; provider keys
are injected at runtime via environment (e.g. `UM_OPENAI_API_KEY`) and are
never stored or logged.

## Run tests

```bash
cd /mnt/data/universal_mind
python -m unittest discover
```

## Swap the store backend

The Executive and registry accept any `MemoryStore` implementation.
`LocalJSONLStore` persists to append-only JSON Lines on disk, while `InMemoryStore` is useful for tests.

## Status

Every README milestone is now implemented and verified: Core / Pantheon /
Memory / Feedback, plus ARETĒ (arbitration), the GATEWAY layer (`io/`),
deployment (a Docker-free `pip install .` package + CLI), Prometheus
self-evolution (reversible apply to the running executive), and the
integration face that closes the loop. The build is closed end-to-end with
`make test` + `make probe` (self-verifying receipt), with the full release gate
`make verify` (lint + mypy ratchet + tests + receipt + probes) printing READY
only when everything is green.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the layering model, the intent
pipeline, ledger schema, and the recovery guide.
