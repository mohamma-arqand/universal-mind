# Universal Mind

A seed-core, local-first orchestration project built around three layers:

- **Core**: identity, intent, clock, errors, and the Executive Mind.
- **Pantheon**: capability contracts and the registry of executable dossiers.
- **Memory / Mnemosyne**: append-only ledger storage and time-aware recall.
- **Feedback**: human verdicts attached to ledger records.
- **ARETĒ**: virtue-based, non-compensatory arbitration of competing candidates
  (`arete/`) — a candidate that violates a hard-gate virtue (Justice by default)
  is disqualified regardless of overall score; excellence ties rule DEFER.
- **Gateway** (`io/`): adapters to external providers — a `Provider` protocol,
  deterministic reference providers (Echo, Scripted), an OpenAI-compatible
  `HttpChatProvider`, and a `Gateway` that retries with backoff and fails over
  across an ordered provider list. API keys resolve lazily via a
  `SecretResolver` and are never stored or logged.

## Deployment

`pyproject.toml` packages the project and exposes a `universal-mind` console
script (see `universal_mind/cli.py`):

- `universal-mind health` — exercises the full stack and prints JSON status;
  exit 0 only when healthy (used as the container `HEALTHCHECK`).
- `universal-mind demo` — the reference end-to-end demo.
- `universal-mind --version` — the package version.

A multi-stage, non-root `Dockerfile` ships a containerized runtime
(`docker build -t universal-mind .`). Provider keys are injected at runtime
via environment (e.g. `UM_OPENAI_API_KEY`); the image contains none.

## Run tests

```bash
cd /mnt/data/universal_mind
python -m unittest discover
```

## Swap the store backend

The Executive and registry accept any `MemoryStore` implementation.
`LocalJSONLStore` persists to append-only JSON Lines on disk, while `InMemoryStore` is useful for tests.

## Not yet implemented

- Prometheus self-evolution
