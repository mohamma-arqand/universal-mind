# Universal Mind — Architecture & Recovery Guide

**Scope:** how the system is layered, how one intent flows through it, what state
it keeps, and how to run, verify, back up, and recover it. This is the
operational map for the `universal_mind` package.

(Build: **177 tests**, ruff-clean, mypy-ratchet within baseline; Docker-free —
a plain `pip install .` package.)

---

## 1. Layering model

`universal_mind/layers.py` defines a numeric layer ladder (substrate-low to
meta-high). A component may call only its own layer, the layer directly below
it, or `MNEMOSYNE` (the special persistent-memory layer any layer may call).

| Layer | Enums / packages | Role |
|-------|------------------|------|
| `0 SUBSTRATE` | `core/clock|identity|errors|models|intent`, `memory/store` | Foundation: time, identity, errors, memory store, intents |
| `1 GATEWAY` | `io/` | Adapters to external systems (LLM/HTTP/MCP/human) |
| `2 PANTHEON` | `pantheon/` | Capability contracts + registry, selection |
| `3 DEMIURGE` | `demiurge/` | Strategic decomposition, strategies, synthesis |
| `4 MNEMOSYNE` | `memory/mnemosyne` | Append-only ledger, recall, decay; callable by all |
| (gate meta) | `gates/` | Gate pipeline (PowerZero, Risk, Policy, Feedback, Layering) |
| (power meta) | `powers/` | Capability powers incl. `Judgment` (verdicts) |
| (super meta) | `arete/`, `prometheus/`, `integration.py` | Arbitration, self-evolution, composed loop |

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
  of score; excellence ties rule DEFER).
- **Gateway** (`io/`) — `Provider` protocol, deterministic reference providers,
  OpenAI-compatible `HttpChatProvider`, and `Gateway` (retry/backoff + failover
  across an ordered provider list; keys via `SecretResolver`, never stored).
- **Prometheus** (`prometheus/`) — **self-evolution**: observe ledger → metrics →
  proposals → conservative policy veto → reversible `ThrottleApplier` /
  `FallbackOrderApplier` (via `evolve_and_apply`). Proposals-only by default.
- **Integration** (`integration.py`) — `InMemoryIntegrationHarness` composes
  ExecutiveMind + GatewayCapability + ARETĒ + Prometheus into one
  deterministic, runnable face (`UniversalMindRuntime`).

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
make probe         # 9 self-verifying probes (-> artifacts/*.xml)
make receipt       # verification receipt; fails the build if any gate is red
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