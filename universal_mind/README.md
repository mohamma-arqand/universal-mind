# Universal Mind

A seed-core, local-first orchestration project built around three layers:

- **Core**: identity, intent, clock, errors, and the Executive Mind.
- **Pantheon**: capability contracts and the registry of executable dossiers.
- **Memory / Mnemosyne**: append-only ledger storage and time-aware recall.
- **Feedback**: human verdicts attached to ledger records.
- **ARETĒ**: virtue-based, non-compensatory arbitration of competing candidates
  (`arete/`) — a candidate that violates a hard-gate virtue (Justice by default)
  is disqualified regardless of overall score; excellence ties rule DEFER.

## Run tests

```bash
cd /mnt/data/universal_mind
python -m unittest discover
```

## Swap the store backend

The Executive and registry accept any `MemoryStore` implementation.
`LocalJSONLStore` persists to append-only JSON Lines on disk, while `InMemoryStore` is useful for tests.

## Not yet implemented

- Gateway to real providers (the `io/` layer is only the GATEWAY contract, empty)
- Prometheus self-evolution
- Deployment shape
