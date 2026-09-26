"""R48 wave 3 — the environment lock: the interpreter gate.

Item 9: py.sh resolves the REAL interpreter deterministically; the
      interpreter gate FAILS LOUDLY when the active python cannot
      import the platform's own dependencies (the outage lesson).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=cwd or ROOT.parent, timeout=300)


class TestInterpreterLock:
    def test_py_sh_resolves_a_real_interpreter(self) -> None:
        r = _run(["bash", str(SCRIPTS / "py.sh")])
        assert r.returncode == 0, r.stderr
        exe = r.stdout.strip()
        assert exe and "python" in exe.lower()
        # and it actually carries the platform's dependencies
        probe = subprocess.run(
            [exe, "-c", "import numpy, pytest, sklearn"],
            capture_output=True, timeout=120)
        assert probe.returncode == 0

    def test_gate_passes_on_the_right_interpreter(self) -> None:
        r = _run([sys.executable, str(SCRIPTS / "interpreter_gate.py")])
        assert r.returncode == 0, r.stdout + r.stderr
        assert "PASS" in r.stdout

    def test_gate_message_names_the_fix_when_wrong(self) -> None:
        # a python without the deps must FAIL LOUDLY with the fix inside
        import os

        hermes_venv = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(hermes_venv) / "hermes" / "hermes-agent" / "venv" / "Scripts" / "python.exe",
        ]
        real = next((c for c in candidates if c.exists()), None)
        if real is None:  # pragma: no cover — CI without the hermes venv
            pytest.skip("hermes venv not present on this host")
        assert real is not None  # for the type checker
        # 3.14 bare python (no numpy) — the outage scenario itself
        wrong = shutil.which("python")
        if wrong is None or wrong == str(real):
            pytest.skip("no wrong interpreter to prove the loud failure")
        assert wrong is not None
        probe = subprocess.run(
            [wrong, "-c", "import numpy, pytest, sklearn"],
            capture_output=True, timeout=120)
        if probe.returncode == 0:
            pytest.skip("the PATH python carries deps — nothing to prove")

        r2 = subprocess.run(
            [wrong, str(SCRIPTS / "interpreter_gate.py")],
            capture_output=True, text=True, timeout=300)
        assert r2.returncode == 3
        assert "FAIL" in r2.stdout
        # the message must hand the operator the fix, not just the pain
        assert ("UM_PYTHON" in r2.stdout or "py.sh" in r2.stdout
                or real.name in r2.stdout)

    def test_verify_gate_summary_includes_interpreter(self) -> None:
        src = (SCRIPTS / "verify.py").read_text(encoding="utf-8")
        assert '("interpreter"' in src
        assert "probe_r48_mind.py" in src
