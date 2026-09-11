"""Test that the showcase runs end-to-end (the 'stranger can run it' gate)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_showcase_runs_clean() -> None:
    """`python scripts/showcase.py` exits 0 — a stranger gets the full trace."""
    repo = Path(__file__).resolve().parent.parent
    script = repo / "scripts" / "showcase.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = proc.stdout
    # Key layers must appear in the trace.
    assert "MOUTH" in out
    assert "ARET" in out
    assert "Metacognition" in out
    assert "Self-awareness" in out
    assert "DONE" in out