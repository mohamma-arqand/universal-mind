# Universal Mind — Architecture & Recovery Guide

**Scope:** how the system is layered, how one intent flows through it, what state
it keeps, and how to run, verify, back up, and recover it. This is the
operational map for the `universal_mind` package.

(Build: **342 tests**, ruff-clean, whole-package mypy 0; Docker-free — a plain
`pip install .` package.)

---

## 1. Layering model

`universal_mind/layers.py` defines the charter's seven-layer stack (L0..L6) plus
the perpendicular MNEMOSYNE. A component may call its own layer or the layer
directly below it; MNEMOSYNE is callable by any layer but calls only
SUBSTRATE. `gates/layering.py` + `tests/test_layering.py` enforce this with an
AST pass that *fails* on any upward import.

| Layer | Enums / packages | Role |
|-------|------------------|------|
| `0 SUBSTRATE` | `core/clock\|identity\|errors\|models\|intent`, `memory/store`, `layers` | Foundation: time, identity, errors, memory store, intents |
| `1 GATEWAY` | `io/` | Adapters to external systems (LLM/HTTP/MCP/human) |
| `2 PANTHEON` | `pantheon/`, `gates/`, `observability/` | Capability contracts + registry, selection |
| `3 DEMIURGE` | `demiurge/`, `synthesis.py`, `compose.py`, `powers/` | Strategic decomposition, strategies, *true* synthesis |
| `4 ARETĒ` | `arete/`, `feedback/` | Judgment — defines "better" (non-compensatory virtue arbitration, consent) |
| `5 PROMETHEUS` | `prometheus/`, `integration.py`, `lifecycle.py`, `durable.py` | Recursive self-improvement (observe → propose → vet → apply, reversible) |
| `6 MOUTH` | `mouth/`, `sovereign.py` | The sole user interface — one identity, one point of interaction |
| `⟂ MNEMOSYNE` | `memory/mnemosyne`, `memory/lifespan` | Append-only ledger, recall, lifespan/decay; callable by all |

## 2. Subsystem map

- **Core / Executive** (`core/executive.py`) — `ExecutiveMind` orchestrates one
  intent through a pre-execution pipeline and writes an audit trail.
- **Pantheon** (`pantheon/`) — `Capability` + `CapabilityDossier` + `PantheonRegistry`
  (capability selection, retry/fallback metadata, secret-name validation).
- **Memory / Mnemosyne** (`memory/`) — append-only `MemoryStore` (`InMemoryStore`,
  `LocalJSONLStore` with tombstones + compaction) and `Mnemosyne` (recall,
  TTL classification, `decay()`).
- **Feedback** (`feedback/`) — `FeedbackChannel`/`HumanFeedbackGate` attach human
  verdicts (approved/rejected/needs_work) to ledger records.
- **Gates** (`gates/`) — unified `PrecedencePipeline` with a frozen precedence
  order: PowerZero (absolute veto) → Layering → Policy → Risk → HumanFeedback.
- **ARETĒ** (`arete/`) — non-compensatory **virtue arbitration** of competing
  candidates (a candidate failing a hard-gate virtue is disqualified regardless
  of score; excellence ties rule DEFER). `StandardKeeper` (the critical loop)
  grants a D the standing standard only by merit, with `rollback()` to rewind
  a lineage; `feedback/consent.py` gates promotions on human consent.
- **Gateway** (`io/`) — `Provider` protocol, deterministic reference providers,
  OpenAI-compatible `HttpChatProvider` (multimodal-capable `Message.parts`),
  an offline `StubChatServer`, and `Gateway` (retry/backoff + failover across
  an ordered provider list; keys via `SecretResolver`, never stored).
- **Prometheus** (`prometheus/`) — **self-evolution**: observe ledger → metrics →
  proposals → conservative policy veto → reversible `ThrottleApplier` /
  `FallbackOrderApplier` (via `evolve_and_apply`) plus the
  `sandbox→benchmark→accept/reject` loop (`evolve.py`). Proposals-only by default.
- **Synthesis** (`synthesis.py` + `compose.py`) — `SynthesisEngine` decomposes,
  resolves specialists, and *fuses* their output into D (`method='fusion'`) —
  true synthesis, not integration — then arbitrates D itself before commit.
- **Power Zero, executable** (`powers/generator.py`) — generates a runnable power,
  sandboxes + benchmarks + arbitrates it, minting only accepted powers below
  all built-ins.
- **Lifecycle** (`lifecycle.py`) — chains mint → remember → consent into one loop.
- **Sovereign** (`sovereign.py`) — distills the ledger into a continuous self
  ("one identity") injected into every interaction.
- **Integration** (`integration.py`) — `InMemoryIntegrationHarness` composes
  ExecutiveMind + GatewayCapability + ARETĒ + Prometheus into one
  deterministic, runnable face (`UniversalMindRuntime`).
- **Observability** (`observability/`) — `Recorder` protocol +
  `NullRecorder`/`MemoryRecorder`; the executive emits execution events.

## 3. The intent pipeline (`ExecutiveMind.handle`)

1. **Contract validation** — `Intent.assert_complete` / `validates_params`
   (caller fault; raises `IntentIncomplete`, records nothing).
2. **Audit record** — `intent_received`.
3. **Composite gate** — `PowerZero → Layering → Policy → Risk → HumanFeedback`
   (a DENY short-circuits; gate decisions are recorded).
4. **Throttle** — `ExecutionThrottle.should_allow`, excluding caller faults from
   the error rate.
5. **Execute** — with idempotency-gated retries (backoff + jitter) and a
   fallback capability chain; `TaskFailure` retried, `SystemFault`/`CallerFault`
   never.
6. **Record result** — `capability_result` (+ `fault` on failure) and a
   `ExecutionRecord`.

Selection: exact goal match → substring match → first registered dossier.

## 4. Ledger record kinds

`capability_registration`, `intent_received`, `risk_assessment`,
`capability_selected`, `capability_result`, `fault`, `strategic_decision`,
`feedback`. These are the substrate for Prometheus metrics and the audit trail.

## 5. Deployment (Docker-free)

```
pip install .                 # installs the 'universal-mind' console script
universal-mind health         # exercise the stack, JSON status, exit 0 iff healthy
universal-mind demo           # reference end-to-end demo
universal-mind interactive    # REPL driving the composed integration harness
universal-mind --version
```

Provider keys are read lazily from the environment (e.g. `UM_OPENAI_API_KEY`)
via `SecretResolver`; the package never embeds or logs secrets.

## 6. Build / verification closure

```
make lint          # ruff check
make typecheck     # mypy --strict
make mypy-ratchet  # fails if mypy debt rises above the versioned baseline
make test          # pytest (-> artifacts/junit.xml)
make probe         # 16 self-verifying probes (-> artifacts/*.xml)
make receipt       # verification receipt; fails the build if any gate is red
python scripts/verify.py   # the same release gate without make (writes READY)
```

The ratchet means **new code must not add mypy debt**: annotate fully and keep
new files type-clean.

## 7. Recovery & troubleshooting

- **State lives where?** Memory is backend-dependent: `InMemoryStore` (volatile,
  tests/demos) vs `LocalJSONLStore` (append-only JSON Lines on disk). Ledger
  records are the single source of truth for audit + Prometheus.
- **Backup:** the ledger files (for a local store) are safe to copy while
  running (append-only). The repo's git history is the source-of-truth snapshot;
  `backups/` holds phase manifests + sha256 ledgers.
- **Broken state:** because records are append-only and gates/prometheus are
  deterministic reads, replaying a ledger reproduces the same decisions.
  `LocalJSONLStore.delete` writes tombstones and auto-compacts; if a tombstone
  run is unexpected, restore from backup, do not hand-edit.
- **Secrets leaked by accident:** revoke the key, then read it only via
  `SecretResolver` from a safe env source; never put it in a ledger record,
  cache, or log.
- **A gate blocks an intent you expect to pass:** inspect the gate decision
  (recorded) — PowerZero veto, Risk policy (reversible+strict exception),
  HumanFeedback history, or throttle error-rate.
- **Self-evolution did something you dislike:** `ThrottleApplier` /
  `FallbackOrderApplier` are reversible — restore the prior knob value (their
  `undo`), which is exactly what they record before mutating.

## 8. Where to add new code

Follow the codebase conventions: a `Protocol` + a deterministic in-memory
reference implementation, a pytest module in `tests/`, and (for a new
subsystem) a self-verifying probe in `scripts/` wired into `make probe`.
Keep it **type-clean** (mypy ratchet), **ruff-clean**, and **Docker-free**.