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

import os
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
    """The interpreter that actually carries the platform's dependencies.

    R48-9: an outage once left ``python`` pointing at a dependency-less
    build; verify would have blessed a green run that never imported.
    Resolution now mirrors scripts/py.sh: UM_PYTHON → the Hermes venv
    (the interpreter every round was built on) → py -3.11 … — and each
    candidate must PROVE it imports numpy+pytest+sklearn before use.
    """
    import os
    import subprocess

    def _carries(exe: str) -> bool:
        try:
            return subprocess.run(
                [exe, "-c", "import numpy, pytest, sklearn"],
                capture_output=True, timeout=60).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    override = os.environ.get("UM_PYTHON")
    if override and _carries(override):
        return override
    homep = os.environ.get("LOCALAPPDATA") or ""
    candidates = [
        f"{homep}/hermes/hermes-agent/venv/Scripts/python.exe" if homep else "",
        "C:/Users/EliteBook/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe",
    ]
    for exe in candidates:
        if exe and _carries(exe):
            return exe
    import shutil

    if shutil.which("py"):
        for minor in (11, 12, 13):
            tag = f"3.{minor}"
            if _carries("py") and subprocess.run(
                ["py", f"-{tag}", "-c", "import numpy, pytest, sklearn"],
                capture_output=True, timeout=60).returncode == 0:
                found = subprocess.run(
                    ["py", f"-{tag}", "-c", "import sys; print(sys.executable)"],
                    capture_output=True, text=True, timeout=30)
                exe = found.stdout.strip()
                if exe:
                    return exe
    # last resort: sys.executable — verify's own gate below will FAIL
    # LOUDLY if this interpreter is missing the platform's dependencies.
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
    "probe_shared.py",
    "probe_persistent_identity.py",
    "probe_deploy_metrics.py",
    "probe_metacognition.py",
    "probe_audit_rubric.py",
    "probe_superplatform_connectors.py",
    "probe_real_media.py",
    "probe_media_pipeline.py",
    "probe_persian_loop.py",
    "probe_arete_run_judgment.py",
    "probe_planning_gate.py",
    "probe_perception_loop.py",
    "probe_full_report.py",
    "probe_autonomous_loop.py",
    "probe_reading_loop.py",
    "probe_agent_loop.py",
    "probe_autonomous_agent.py",
    "probe_honesty_pressure.py",
    "probe_crown_cycle.py",
    "probe_operator_experience.py",
    "probe_audit_holds.py",
    "probe_the_leaps.py",
    "probe_quantum_leaps_2.py",
    "probe_deep_debug_holds.py",
    "probe_intelligence_layer.py",
    "probe_reflexive.py",
    "probe_honest_ask.py",
    "probe_conversational.py",
    "probe_r37_upgrade.py",
    "probe_r38_upgrade.py",
    "probe_r39_recovery.py",
    "probe_r40_survival.py",
    "probe_r41_remaining.py",
    "probe_r42_holes.py",
    "probe_r43_refusals.py",
    "probe_r44_wave1.py",
    "probe_r44_verdict_ui.py",
    "probe_r44_crossx.py",
    "probe_r44_red_team.py",
    "probe_r44_ab_rescue.py",
    "probe_r44_wave3.py",
    "probe_r44_absorption_recipe.py",
    "probe_r44_store_economy.py",
    "probe_r44_tick_pulse.py",
    "probe_r44_drift.py",
    "probe_r44_restore_drill.py",
    "probe_r44_yearbook.py",
    "probe_r45_wave1.py",
    "probe_r45_wave2.py",
    "probe_r45_wave3.py",
    "probe_r45_life.py",
    "probe_r46_day.py",
    "probe_r47_mind.py",
    "probe_r48_mind.py",
    "probe_r53_waves.py",
    "probe_r57_adversarial.py",
    "probe_r57_quarantine.py",
    "probe_r57_ssrf.py",
    "probe_r57_ledger.py",
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
    # Pinned: uvx resolves to the latest ruff, and a new minor version added
    # E-rules (E402/E712/E731/E741) that flag pre-existing intentional patterns
    # across the suite — pinning keeps the gate measuring *our* rules, not ruff's
    # version drift.
    import shutil
    import subprocess as sub

    probe = sub.run(
        ["uvx", "ruff@0.15.18", "--version"], capture_output=True, timeout=90, check=False,
    )
    if probe.returncode != 0:
        # OFFLINE FALLBACK (the sandboxed-host lesson): uvx needs the network
        # to materialize the pinned ruff; on a cut-off host the SAME pinned
        # version installed in the runtime venv is the honest substitute —
        # same tool, same version, measured (not assumed) below.
        local = shutil.which("ruff") or str(
            Path(__file__).resolve().parents[2] / "hermes-agent" / "venv" / "Scripts" / "ruff.exe"
        )
        cand = [local]
        hermes_ruff = Path(
            os.environ.get("LOCALAPPDATA", "")
        ) / "hermes" / "hermes-agent" / "venv" / "Scripts" / "ruff.exe"
        if hermes_ruff.exists():
            cand.insert(0, str(hermes_ruff))
        for exe in cand:
            if exe and Path(exe).exists():
                ver = sub.run([exe, "--version"], capture_output=True, text=True, timeout=60, check=False)
                if "0.15.18" in (ver.stdout or ""):
                    print(f"  [offline] using pinned ruff at {exe}")
                    return _sh([exe, "check", "universal_mind/", "universal_mind/tests/"], check=False)
        print("  [lint] no pinned ruff reachable (uvx offline, venv missing)")
        return 2
    return _sh(["uvx", "ruff@0.15.18", "check", "universal_mind/", "universal_mind/tests/"], check=False)


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
    import sys as _sys

    failed: list[str] = []
    for probe in PROBES:
        out = _sh(
            [HOST_PYTHON, f"scripts/{probe}", f"--junit-xml={ARTIFACTS / (probe[:-3] + '.xml')}"],
            cwd=ROOT,
            check=False,
            env=env,
        )
        if out != 0:
            failed.append(probe)
            print(f"  [RED] {probe} (exit {out})", flush=True)
            _sys.stderr.flush()
        rc = rc or out
    if failed:
        print(f"probes failed: {failed}", flush=True)
    return rc


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    # R48-9 — THE INTERPRETER GATE runs first: a green VERIFY on an
    # interpreter that cannot even import the platform's dependencies
    # would be a lie. resolve() picks the real interpreter (py.sh logic);
    # gate() proves THIS process can run the platform's code.
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from interpreter_gate import (  # type: ignore[import-not-found]
        interpreter_gate as _gate_fn)

    gate_ok, _gate_msg = _gate_fn()
    gates: list[tuple[str, int]] = [
        ("interpreter", 0 if gate_ok else 1),
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