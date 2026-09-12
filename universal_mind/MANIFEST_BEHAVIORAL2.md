# MANIFEST — behavioral-bug sweep, round 2

Continuing the "absence-as-success" hunt into the remaining core modules.

- [x] H1 memory/mnemosyne.py  — empty query returned every fresh record → now []
- [x] H2 core/executive.py    — audited: retry loop = max_retries+1 attempts (correct); throttle caller-fault exclusion correct
- [x] H3 io/gateway.py        — audited: while attempt<=budget = max_retries+1 (correct); socket errors now transient (prior fix)
- [x] H4 arete/lineage.py     — audited: excellence/justice fallback to 0 is degenerate-but-harmless (no false success)
- [x] H5 powers/intent.py     — empty input fabricated 'Unspecified goal' → now raises IntentIncomplete

Success = real bug fixed + locked by test; mypy 0; ruff clean; READY.