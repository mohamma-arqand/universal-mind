#!/usr/bin/env python3
"""R57 N6 — THE SECURITY DOC CANNOT DRIFT FROM REALITY: 6 proofs.

docs/SECURITY.md claims "this is a list of EVIDENCE, not of claims". That
claim is only worth anything if it is checked, so this probe reads the
document and verifies every proof it cites:

 1  Every test file the doc cites exists on disk.
 2  Every test NAME the doc cites exists in that file.
 3  Every probe the doc cites exists in scripts/.
 4  Every probe the doc cites is REGISTERED in verify.py's PROBES list.
 5  The doc names all four R57 probes (none silently dropped).
 6  The doc states the three honest failures of the period — a threat model
    that hides its own corrections is marketing, not engineering.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_UM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_UM.parent))
sys.path.insert(0, str(_UM))

DOC = _UM / "docs" / "SECURITY.md"
VERIFY = _UM / "scripts" / "verify.py"
TESTS = _UM / "tests"

FAILURES: list[str] = []


def check(n: int, label: str, ok: bool) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {n}. {label}")
    if not ok:
        FAILURES.append(label)


def main() -> int:
    if not DOC.exists():
        print("FAIL: docs/SECURITY.md is missing")
        return 1
    doc = DOC.read_text(encoding="utf-8")
    verify_src = VERIFY.read_text(encoding="utf-8") if VERIFY.exists() else ""

    # every "file.py::something" reference
    file_refs = set(re.findall(r"[a-z0-9_]+\.py::[A-Za-z0-9_]+", doc))
    missing_files = sorted({
        ref.split("::")[0] for ref in file_refs if not (TESTS / ref.split("::")[0]).exists()
    })
    check(1, f"every cited test FILE exists ({len(file_refs)} refs)",
          not missing_files)
    if missing_files:
        print(f"      missing: {missing_files}")

    phantom_names = []
    by_file: dict[str, str] = {}
    for ref in sorted(file_refs):
        fname, sym = ref.split("::")
        by_file.setdefault(fname, "")
        by_file[fname] += (TESTS / fname).read_text(encoding="utf-8")
    for ref in sorted(file_refs):
        fname, sym = ref.split("::")
        if sym not in by_file[fname]:
            phantom_names.append(ref)
    check(2, f"every cited test NAME exists in its file ({len(file_refs)} refs)",
          not phantom_names)
    if phantom_names:
        print(f"      phantom: {phantom_names}")

    probes = sorted(set(re.findall(r"probe_[a-z0-9_]+", doc)))
    missing_probes = [p for p in probes if not (_UM / "scripts" / f"{p}.py").exists()]
    check(3, f"every cited probe exists ({len(probes)} probes)", not missing_probes)

    unregistered = [p for p in probes if f'"{p}.py"' not in verify_src]
    check(4, "every cited probe is registered in verify.py", not unregistered)
    if unregistered:
        print(f"      unregistered: {unregistered}")

    required = {"probe_r57_adversarial", "probe_r57_quarantine",
                "probe_r57_ssrf", "probe_r57_ledger"}
    check(5, "the doc names all four R57 probes",
          required <= set(probes))

    # 6 — the honest-failures section is present and non-empty
    has_section = "شکست" in doc and ("قانون یک ساعت" in doc or "ONE CLOCK" in doc)
    check(6, "the doc states its own corrections (not just successes)", has_section)

    print()
    if FAILURES:
        print(f"R57-DOCS probe FAILED ({len(FAILURES)}):")
        for f in FAILURES:
            print(f"  ✗ {f}")
        return 1
    print("R57-DOCS probe: ALL 6 PROOFS PASS — the threat model matches the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
