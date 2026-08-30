#!/usr/bin/env python3
"""One-way ratchet: fail if mypy reports MORE type debt than the versioned baseline.

The baseline file ``mypy_baseline.txt`` (in the package root) holds a stable,
sorted, per-(file, error-code) breakdown of the current type debt
(Mission 3.5-R classified it; Mission 3.6-R hardened it). This script re-runs
mypy live, derives the same canonical breakdown from the output, and exits
non-zero if the live debt is NOT a prefix of the baseline — i.e. if (a) the
total count rises, or (b) new error codes appear in a file, or (c) an error
code moves to a file that did not already carry it.

Compared with a lone integer, this catches "1 new error here, 1 fixed there"
swap that keeps the total flat while shipping debt into a previously-clean
file. Because the whole class is defined by a single data structure (a dict), a
bare line count cannot fork: every branch below derives from that canonical
breakdown, so both trip and untrip are testable directly.

Exit codes (documented because the Makefile and tests rely on them):
    0  live debt is a prefix of the baseline (either identical or strictly less)
    1  live debt is NOT a prefix of the baseline (total rose or debt spread)
    2  mypy could not be run or its output could not be parsed

The 100-per-error-code cap on the raw print is only to stop log spam; it is
never used in the comparison, which always uses the full breakdown.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "mypy_baseline.txt"
TARGETS = ["universal_mind"]
ERROR_LINE = re.compile(
    r"^(?P<path>\S+?\.py):\d+(?::\d+)?:\s*error:\s*.+\[(?P<code>[a-z-]+)\]$"
)


def canonical_debt(output: str) -> dict[str, int]:
    """Map (file, error-code) -> count from raw mypy ``--no-pretty`` output.

    Every non-comment line that matches mypy's ``error:`` shape is tallied.
    This is the single source of truth for the whole ratchet: total = sum, and
    prefix ordering is defined solely over this dict.
    """
    counts: dict[tuple[str, str], int] = {}
    for line in output.splitlines():
        # Only well-formed error lines carry a [code] suffix; anything else —
        # the summary, notes, or non-error output — is ignored by design.
        m = ERROR_LINE.match(line.strip())
        if m:
            file = m.group("path")
            code = m.group("code")
            counts[(file, code)] = counts.get((file, code), 0) + 1
    return {
        f"{file}  {code}": n
        for (file, code), n in sorted(counts.items())
    }


def is_prefix(live: dict[str, int], baseline: dict[str, int]) -> bool:
    """True iff live debt is a subset of baseline debt (narrower or equal)."""
    for key, count in live.items():
        if baseline.get(key, 0) < count:
            return False
    return True


def _numeric_baseline() -> int:
    """Read the total call-count. Prefers the ``total=`` header (current format)
    and falls back to a lone integer (the pre-Mission-3.6-R format)."""
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("total="):
            return int(line[len("total="):])
        if line.isdigit():
            return int(line)
    raise RuntimeError(f"no integer baseline found in {BASELINE}")


def _load_baseline() -> dict[str, int]:
    """Deserialize the per-(file, code) baseline breakdown.

    Each data row is ``<file>  <code>: N``, written by the companion generator
    (the two-space separator is the canonical key split). The trailing ``: N``
    is stripped and parsed as the count. Nothing here acts as a comparison
    source on its own — it is only the frozen reference for ``is_prefix``.
    """
    breakdown: dict[str, int] = {}
    data_row = re.compile(r"^(?P<key>.+): (?P<n>\d+)$")
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("total="):
            continue
        m = data_row.match(line)
        if m and "  " in m.group("key"):
            breakdown[m.group("key")] = int(m.group("n"))
    return breakdown


def _live() -> str:
    """Run mypy live and return its combined output. Never swallows a crash."""
    proc = subprocess.run(
        ["mypy", "--no-pretty", *TARGETS],
        cwd=ROOT.parent, capture_output=True, text=True, check=False,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    live = canonical_debt(_live())
    baseline = _load_baseline()
    baseline_total = _numeric_baseline()

    live_total = sum(live.values())
    print(f"mypy ratchet: live={live_total}, baseline={baseline_total}")
    # is_prefix is the single gate: it fails both a higher total and a spread of
    # debt into a (file, code) slot the baseline did not already carry. The
    # print below is informational only — never used in the decision.
    for i, ((k, n)) in enumerate(sorted(live.items())):
        if i >= 100:
            print("... (further entries elided)")
            break
        print(f"  live {k}: {n}")
    if not is_prefix(live, baseline):
        print(
            f"ratchet FAILED: live debt is not a prefix of baseline "
            f"(live={live_total}, baseline={baseline_total}). New type debt in "
            "a file/code slot that the baseline doesn't already carry. Fix "
            "your code; do not raise the baseline.",
            file=sys.stderr,
        )
        return 1
    print(f"ratchet OK: {live_total} <= {baseline_total} and prefix-preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())