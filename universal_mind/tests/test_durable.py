"""Tests for durable local persistence: the ledger survives restart/reopen."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from universal_mind.durable import PersistentMind
from universal_mind.integration import InMemoryIntegrationHarness, IntegrationError
from universal_mind.io.errors import ProviderPermanent
from universal_mind.io.gateway import Gateway, ScriptedProvider
from universal_mind.memory.store import LocalJSONLStore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_run_persists_ledger_to_disk(tmp_path: Path) -> None:
    """Running the durable face writes a non-empty JSONL ledger file on disk."""
    mind = PersistentMind.open(tmp_path)
    report = mind.run("summarize", "Persist me")
    assert report.ok
    ledger_file = mind.directory / "ledger.jsonl"
    assert ledger_file.exists()
    assert ledger_file.stat().st_size > 0
    assert mind.ledger_size > 0
    assert "capability_result" in mind.ledger_kinds()


def test_reopen_reloads_same_ledger(tmp_path: Path) -> None:
    """Reopening the directory reloads exactly what was written before."""
    first = PersistentMind.open(tmp_path)
    first.run("summarize", "hello")
    n = first.ledger_size

    second = PersistentMind.reopen(tmp_path)
    assert second.ledger_size == n
    assert second.ledger_kinds() == first.ledger_kinds()


def test_durability_across_fresh_process(tmp_path: Path) -> None:
    """A brand-new Python process reopening the directory sees the ledger."""
    mind = PersistentMind.open(tmp_path)
    mind.run("summarize", "cross-process me")
    n = mind.ledger_size

    child = (
        "import os\n"
        "from universal_mind.durable import PersistentMind\n"
        "m = PersistentMind.reopen(os.environ['UM_DURABLE_DIR'])\n"
        "print('LEDGER', m.ledger_size)\n"
        "print('KINDS', m.ledger_kinds())\n"
    )
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT), UM_DURABLE_DIR=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", child], capture_output=True, text=True, env=env, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    assert f"LEDGER {n}" in result.stdout
    assert "capability_result" in result.stdout


def test_recovery_sees_fault_after_reopen(tmp_path: Path) -> None:
    """A failed execution records a fault that a reopened runtime still reads."""
    store = LocalJSONLStore(directory=tmp_path)
    harness = InMemoryIntegrationHarness(Gateway([ScriptedProvider([ProviderPermanent("down")])]), store=store)
    with pytest.raises(IntegrationError):
        harness.run("summarize", "fail")

    reloaded = InMemoryIntegrationHarness(Gateway([ScriptedProvider([ProviderPermanent("down")])]), store=store)
    kinds = {r.get("kind") for r in reloaded.store.read_all()}
    assert "fault" in kinds

    # Prometheus observes the reloaded ledger without error.
    evolution = reloaded._prometheus.evolve()
    assert isinstance(evolution.summary, str)
    assert isinstance(evolution.proposals, tuple)


def test_reopen_is_a_true_file_reload(tmp_path: Path) -> None:
    """Reopening is not memory: dropping the file per process state is re-read."""
    mind = PersistentMind.open(tmp_path)
    mind.run("summarize", "x")
    expected = mind.ledger_size
    # A fresh instance reads straight from disk each time.
    direct = LocalJSONLStore(directory=tmp_path)
    assert sum(1 for _ in direct.read_all()) == expected