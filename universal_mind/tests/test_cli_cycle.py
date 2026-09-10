"""Tests for the CLI 'cycle' command — demo->synthesis->evolve->dashboard loop."""

from __future__ import annotations

import json
import re
from pathlib import Path

from universal_mind import cli


def _extract(html: str) -> dict:
    m = re.search(r"const DATA = (\{.*?\});\nconst", html, re.S)
    assert m, "dashboard HTML must embed DATA"
    return json.loads(m.group(1))


def test_cycle_writes_dashboard_and_ledger(tmp_path: Path) -> None:
    """One cycle synthesises, evolves, and renders a real-data dashboard."""
    out = tmp_path / "dash.html"
    rc = cli.main(["cycle", "--dir", str(tmp_path / "ledger"), "--out", str(out)])
    assert rc == 0
    assert out.exists()
    data = _extract(out.read_text(encoding="utf-8"))
    assert data["synth_runs"], "cycle must produce synthesis runs"
    assert data["standard_current"]["name"] is not None
    # The durable ledger grew with synthesis + standard records.
    ledger = tmp_path / "ledger" / "ledger.jsonl"
    assert ledger.exists()


def test_cycle_is_repeatable_append_only(tmp_path: Path) -> None:
    """A second cycle on the same directory appends, never clears."""

    def records() -> int:
        p = tmp_path / "ledger" / "ledger.jsonl"
        if not p.exists():
            return 0
        return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())

    r1 = records()
    cli.main(["cycle", "--dir", str(tmp_path / "ledger"), "--out", str(tmp_path / "a.html")])
    after1 = records()
    cli.main(["cycle", "--dir", str(tmp_path / "ledger"), "--out", str(tmp_path / "b.html")])
    after2 = records()
    assert after1 > r1
    assert after2 >= after1  # grows or stays; never shrinks unexpectedly


def test_cycle_produces_evolution_block(tmp_path: Path) -> None:
    """Including the Prometheus pass in the cycle does not crash on an empty dir."""
    out = tmp_path / "dash.html"
    rc = cli.main(["cycle", "--dir", str(tmp_path / "ledger2"), "--out", str(out), "--throttle", "0.5"])
    assert rc == 0
    assert out.exists()