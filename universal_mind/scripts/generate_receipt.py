#!/usr/bin/env python3
"""Generate a release-blocking verification receipt from a JUnit XML log.

Parses a JUnit XML test report (produced by :code:`pytest --junitxml=...`)
with the standard-library :mod:`xml.etree.ElementTree` — no third-party
dependency — and emits :file:`verification_receipt.json` with an explicit
:code:`overall` verdict.

Exit code mirrors :code:`overall`: :code:`0` on pass, non-zero on fail. A
missing or malformed XML file is an error: the script exits non-zero and
writes no receipt (no empty/vacuous receipt is ever produced).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"

# Default junit log lives next to the package root (i.e. universal_mind/artifacts/junit.xml).
_DEFAULT_JUNIT = Path(__file__).resolve().parent.parent / "artifacts/junit.xml"


def _git_commit() -> str | None:
    """Return the current HEAD commit hash, or None if git is unavailable.

    Never fabricates a placeholder string — a genuine failure resolves to
    JSON ``null`` so a stale/fake signal cannot be mistaken for a real one.
    """
    here = Path(__file__).resolve().parent
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=here, capture_output=True, text=True, check=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=toplevel, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return head or None
    except (subprocess.CalledProcessError, OSError):
        return None


def _parse_metrics(xml_path: Path) -> dict[str, int]:
    """Aggregate test counters from a JUnit <testsuite>(s) document."""
    try:
        root = ET.parse(str(xml_path)).getroot()
    except ET.ParseError as exc:
        raise RuntimeError(f"malformed JUnit XML {xml_path}: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"cannot read JUnit XML {xml_path}: {exc}") from exc

    suites = root if root.tag == "testsuites" else [root]
    records = [s for s in suites if s.tag == "testsuite"]
    if not records:
        raise RuntimeError(f"no <testsuite> element found in {xml_path}")

    def _int(suite: ET.Element, attr: str) -> int:
        raw = suite.get(attr)
        if raw is None or not raw.isdigit():
            return 0
        return int(raw)

    return {
        "tests": sum(_int(s, "tests") for s in records),
        "failures": sum(_int(s, "failures") for s in records),
        "errors": sum(_int(s, "errors") for s in records),
        "skipped": sum(_int(s, "skipped") for s in records),
    }


def build_receipt(
    xml_path: Path,
    output_path: Path,
    lint_status: str | None = None,
) -> tuple[dict[str, object], str]:
    """Return (receipt_dict, overall). Raises RuntimeError on fatal input errors."""
    metrics = _parse_metrics(xml_path)
    tests, failures, errors = metrics["tests"], metrics["failures"], metrics["errors"]

    checks: list[dict[str, str]] = [
        {"name": "tests.nonempty", "status": "pass" if tests > 0 else "fail"},
        {"name": "tests.failures", "status": "pass" if failures == 0 else "fail"},
        {"name": "tests.errors", "status": "pass" if errors == 0 else "fail"},
    ]
    if lint_status is not None:
        checks.append({"name": "lint", "status": lint_status})

    # overall === 'pass' iff every check passes. Required checks are the union
    # above: no optional/soft checks exist unless --lint adds a required one.
    overall = "pass" if all(c["status"] == "pass" for c in checks) else "fail"

    receipt: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),  # None -> JSON null
        "tests": metrics,
        "checks": checks,
        "overall": overall,
    }
    return receipt, overall


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "junit_xml", nargs="?", default=str(_DEFAULT_JUNIT),
        help="path to JUnit XML log (default: artifacts/junit.xml)",
    )
    parser.add_argument(
        "--lint", choices=["pass", "fail", "skip"], default=None,
        help="attach a lint check with the given status",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="receipt output path (default: artifacts/verification_receipt.json)",
    )
    args = parser.parse_args(argv)

    xml_path = Path(args.junit_xml)
    output_path = Path(args.output) if args.output else (
        Path(__file__).resolve().parent.parent / "artifacts" / "verification_receipt.json"
    )

    try:
        receipt, overall = build_receipt(xml_path, output_path, lint_status=args.lint)
    except RuntimeError as exc:
        print(f"generate_receipt: ERROR: {exc}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"generate_receipt: wrote {output_path} (overall={overall})")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())