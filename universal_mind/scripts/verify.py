#!/usr/bin/env python3
"""Run the full release gate and write the READY stamp (make verify, without make).

Mirrors the Makefile's ``verify`` target exactly — lint → mypy ratchet → tests
(with JUnit) → receipt → probes — and writes ``artifacts/verification_status.txt``
= ``READY`` only if every gate is green. This makes the release gate runnable
anywhere python is, regardless of whether ``make`` (or the historic WSL venv)
is present on the host.

Exit 0 on READY, non-zero otherwise.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # universal_mind/
REPO = ROOT.parent
ARTIFACTS = ROOT / "artifacts"
JUNIT = ARTIFACTS / "junit.xml"
RECEIPT = ARTIFACTS / "verification_receipt.json"
STATUS = ARTIFACTS / "verification_status.txt"


def _host_python() -> str:
    """Return the interpreter that can run pytest cleanly on this host.

    On this machine the runtime ``python`` (3.11) runs the whole suite green,
    whereas the user-installed 3.14 has a stricter socket path that trips one
    localhost HTTP test — so we prefer ``sys.executable`` (whatever launched
    this script) unless an explicit ``UM_PYTHON`` override is given.
    """
    import os
    import sys

    override = os.environ.get("UM_PYTHON")
    if override:
        return override
    return sys.executable


HOST_PYTHON = _host_python()

# All probes, in the Makefile's order.
PROBES = [
    "probe_precedence_immutability.py",
    "probe_powerzero_terminal.py",
    "probe_tombstone_bound.py",
    "probe_decay_bounds.py",
    "probe_arete_arbitration.py",
    "probe_io_gateway.py",
    "probe_prometheus_evolution.py",
    "probe_integration_loop.py",
    "probe_evolution_apply.py",
    "probe_durability.py",
    "probe_evolution_loop.py",
    "probe_synthesis_loop.py",
    "probe_arete_standard.py",
    "probe_augment_capabilities.py",
    "probe_lifecycle.py",
    "probe_continuous_judgment.py",
    "probe_closed_loop.py",
    "probe_independent_evaluation.py",
    "probe_evolutionary_architecture.py",
    "probe_scale_durability.py",
    "probe_counterfactual.py",
    "probe_hypotheses.py",
    "probe_causal.py",
    "probe_episodic.py",
    "probe_induction.py",
    "probe_uncertainty.py",
    "probe_cross_judge.py",
    "probe_goal_drift.py",
    "probe_self_code_audit.py",
    "probe_rubric_learning.py",
    "probe_red_team.py",
    "probe_policy_trace.py",
    "probe_multilingual.py",
    "probe_temporal_awareness.py",
    "probe_real_tools.py",
]


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True, text=True, check=check, env=env)


def _sh(cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> int:
    proc = _run(cmd, cwd=cwd, check=check, env=env)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def step_lint() -> int:
    print("\n=== lint (ruff) ===")
    return _sh(["uvx", "ruff", "check", "universal_mind/", "universal_mind/tests/"], check=False)


def step_mypy_ratchet() -> int:
    print("\n=== mypy ratchet ===")
    return _sh([HOST_PYTHON, "scripts/check_mypy_ratchet.py"], cwd=ROOT, check=False)


def step_tests() -> int:
    print("\n=== tests (pytest, JUnit) ===")
    import os

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env2 = dict(os.environ)
    env2["PYTHONPATH"] = str(REPO)
    proc = subprocess.run(
        [HOST_PYTHON, "-m", "pytest", "-q", "--tb=short", f"--junitxml={JUNIT}", "tests/"],
        cwd=str(ROOT), capture_output=True, text=True, check=False, env=env2,
    )
    print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def step_receipt() -> int:
    print("\n=== receipt ===")
    return _sh([HOST_PYTHON, "scripts/generate_receipt.py", str(JUNIT)], cwd=ROOT, check=False)


def step_probes() -> int:
    print("\n=== probes ===")
    import os

    rc = 0
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    for probe in PROBES:
        out = _sh(
            [HOST_PYTHON, f"scripts/{probe}", f"--junit-xml={ARTIFACTS / (probe[:-3] + '.xml')}"],
            cwd=ROOT,
            check=False,
            env=env,
        )
        rc = rc or out
    return rc


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    gates: list[tuple[str, int]] = [
        ("lint", step_lint()),
        ("mypy-ratchet", step_mypy_ratchet()),
        ("tests", step_tests()),
        ("receipt", step_receipt()),
        ("probes", step_probes()),
    ]
    print("\n================ GATE SUMMARY ================")
    ok = True
    for name, rc in gates:
        status = "GREEN" if rc == 0 else "RED"
        print(f"  {name}: {status} (exit {rc})")
        ok = ok and rc == 0

    if ok:
        STATUS.write_text("READY\n", encoding="utf-8")
        print("\n===================================================")
        print(" VERIFICATION: READY  (lint + ratchet + tests + receipt + probes)")
        print("===================================================")
        return 0
    print("\nVERIFICATION FAILED — one or more gates are red.")
    return 1


if __name__ == "__main__":
    sys.exit(main())