# Universal Mind

A seed-core, local-first orchestration project built around three layers:

- **Core**: identity, intent, clock, errors, and the Executive Mind.
- **Pantheon**: capability contracts and the registry of executable dossiers.
- **Memory / Mnemosyne**: append-only ledger storage and time-aware recall.
- **MOUTH** (`mouth/`): the sole input gate — raw speech becomes a
  `StructuredIntent` (goal, success criteria, constraints, determinism), each
  committed field anchored to an `EvidenceBundle` pointing at the raw-text span
  it came from. A vague or self-contradicting request is refused with an
  `IntentNeedsClarification`/`IntentConflict`, never silently committed.
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
  Recursive self-improvement (`prometheus/evolve.py`) enforces the governing
  rule `code → sandbox → benchmark → accept/reject`: a candidate is built in an
  isolated sandbox, scored against a benchmark, and the `EvolutionGate` accepts
  it only when it measurably beats the baseline — with a mandatory evidence
  bundle. Nothing a self-modification produces ever lands in the live tree.
- **Integration** (`integration.py`): the composed face that closes the loop —
  a `GatewayCapability` runs inside the ExecutiveMind, the produced output is
  arbitrated by ARETĒ against a baseline, and Prometheus watches the same
  ledger. `InMemoryIntegrationHarness` makes the whole system runnable and
  deterministic with an injected provider.
- **Durable** (`durable.py`): `PersistentMind` binds the composed runtime to an
  on-disk `LocalJSONLStore`, so the ledger survives a restart. Registration is
  idempotent across reopens (`PantheonRegistry.restore_capability`), letting a
  reopen reload the same ledger and recover recorded faults.
- **Power Zero, executable** (`powers/generator.py`): the charter's answer to
  "do 37 powers cover infinity?". `PowerZeroGenerator` emits a real runnable
  power as Python source, builds + imports it in a throwaway sandbox,
  benchmarks it, and lets ARETĒ's non-compensatory rule accept/reject it.
  Accepted powers are minted via `PowerZero` strictly below all 7 built-ins
  and never land in the live tree — the mind grows without losing its bounds.
- **Remembering Mnemosyne** (`memory/mnemosyne.py → query()`): inferential
  recall — ranks ledger records by lexical relevance + freshness (never pure
  recency), so the memory substrate feeds the Demiurge rather than only
  auditing it.
- **Human-in-the-loop** (`feedback/consent.py`): `PromotionConsent` wraps the
  `StandardKeeper` so an ARETĒ promotion is *provisional* until a human
  consents or vetoes it; the ruling is committed as first-class
  `HUMAN`/`CONSENT` evidence (the highest-trust source). Deny-by-default.

## Deployment

`pyproject.toml` packages the project and exposes a `universal-mind` console
script (see `universal_mind/cli.py`):

- `universal-mind health` — exercises the full stack and prints JSON status;
  exit 0 only when healthy.
- `universal-mind demo` — the reference end-to-end demo.
- `universal-mind interactive` — REPL over the composed harness (local providers).
- `universal-mind chat [--local]` — REPL wired to a real OpenAI-compatible
  provider. With `--local` it spins up the offline `StubChatServer` (no key, no
  network) and drives the full GATEWAY→provider wire path deterministically;
  otherwise it reads `UM_OPENAI_BASE_URL`, `UM_OPENAI_MODEL`,
  `UM_OPENAI_API_KEY` from the environment (fail-safe without a key).
- `universal-mind dashboard --out <path>` — build a self-contained, real-data
  dashboard HTML (see **Dashboard** below).
- `universal-mind cycle --dir <dir> --out <path>` — run one full
  demo→synthesis→ARETĒ→evolve→dashboard loop over a durable ledger directory
  (append-only; repeatable).
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

## Dashboard

`universal-mind dashboard --out dashboard.html` (or `cycle`) writes a single
self-contained HTML file — no server, no external fetch. It is **not a
mockup**: it runs the actual SynthesisEngine and ARETĒ critical loop against a
durable ledger and renders exactly what that run committed — the seven layers
(+ MNEMOSYNE), the standing standard and its promotion trail, synthesis runs,
the specialist contract registry, and the ledger composition. The quality gate
measures the pytest suite size at build time, so the "tests pass" count never
drifts from the code.

## Run tests

```bash
cd <repo-root>/universal_mind
PYTHONPATH=.. python -m pytest -q tests/
```

Run the self-verifying probes and the full release gate:

```bash
make probe   # all probes, with JUnit XML receipts
make verify  # lint + mypy ratchet + tests + receipt + probes -> READY
```

(`make` targets live in `universal_mind/Makefile`; invoke them from inside
`universal_mind/`.)

## Swap the store backend

The Executive and registry accept any `MemoryStore` implementation.
`LocalJSONLStore` persists to append-only JSON Lines on disk, while `InMemoryStore` is useful for tests.

## Status

Every README milestone is now implemented and verified: Core / Pantheon /
Memory / Feedback, plus ARETĒ (arbitration + the critical-loop `StandardKeeper`),
the GATEWAY layer (`io/`, including the offline OpenAI-compatible stub server),
deployment (a Docker-free `pip install .` package + CLI), Prometheus
self-evolution (reversible apply to the running executive + the
`sandbox→benchmark→accept/reject` loop), the synthesis engine (A+B+C→D), and
the real-data dashboard. The build is closed end-to-end with `make test` +
`make probe` (self-verifying receipt), with the full release gate `make verify`
(lint + mypy ratchet + tests + receipt + probes) printing READY only when
everything is green.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the layering model, the intent
pipeline, ledger schema, and the recovery guide.
