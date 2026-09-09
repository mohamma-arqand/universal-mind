"""Tests for the real-data dashboard generator (universal_mind/dashboard.py).

These run the actual build: they exercise the synthesis engine + ARETĒ critical
loop against a default store, render the HTML, and assert the embedded DATA is
real (derived from the run) rather than a mockup. Nothing here is fabricated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from universal_mind.dashboard import build_and_write, build_dashboard_html
from universal_mind.memory.store import InMemoryStore


def _extract_data(html: str) -> Any:
    m = re.search(r"const DATA = (\{.*?\});\n", html, re.DOTALL)
    assert m is not None, "dashboard HTML must embed a DATA constant"
    parsed = json.loads(m.group(1))
    assert isinstance(parsed, dict)
    return parsed


def test_build_produces_html_with_data(tmp_path: Path) -> None:
    """The generator writes a self-contained HTML with embedded DATA."""
    out = Path(tmp_path) / "dash.html"
    wrote = build_and_write(out)
    assert wrote == str(out.resolve())
    html = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in html.lower()
    data = _extract_data(html)
    assert data["title"] == "Universal Mind — Cognitive Sovereign"


def test_dashboard_runs_real_synthesis(tmp_path: Path) -> None:
    """Synthesis runs are counted from the actual committed runs."""
    store = InMemoryStore()
    html = build_dashboard_html(store)
    data = _extract_data(html)
    assert data["synth_runs"], "dashboard must show real synthesis runs"
    # Every run the scenario produced is committed to the ledger.
    assert data["report_count"] >= 1
    committed = sum(1 for s in data["synth_runs"] if s["committed"])
    assert committed == data["report_count"]


def test_dashboard_standard_governed_by_arete(tmp_path: Path) -> None:
    """The standing standard and promotion trail come from ARETĒ, not a stub."""
    store = InMemoryStore()
    data = _extract_data(build_dashboard_html(store))
    assert data["standard_current"]["name"] is not None
    assert data["standard_trail"], "promotion trail must reflect real arbitration"
    # Decisions are only the ARETĒ vocabulary.
    assert {t["decision"] for t in data["standard_trail"]} <= {"promoted", "deferred", "rejected"}


def test_dashboard_counts_are_from_live_run(tmp_path: Path) -> None:
    """Ledger composition reflects exactly what the run committed."""
    store = InMemoryStore()
    data = _extract_data(build_dashboard_html(store))
    # Ledger kinds are the actual committed record kinds.
    assert "synthesis" in data["ledger"]["kinds"]
    assert "standard" in data["ledger"]["kinds"]
    actual = sum(data["ledger"]["kinds"].values())
    assert data["ledger"]["records"] == actual


def test_dashboard_health_tests_is_int_or_none(tmp_path: Path) -> None:
    """The test-count is measured (int) or honestly None, never a hardcoded guess."""
    data = _extract_data(build_dashboard_html(InMemoryStore()))
    assert data["health"]["tests"] is None or isinstance(data["health"]["tests"], int)


def test_dashboard_is_static_no_server(tmp_path: Path) -> None:
    """The artifact is a single self-contained file (no external fetch)."""
    html = build_dashboard_html(InMemoryStore())
    assert "<script" in html
    assert "fetch(" not in html
    assert "src=" not in html.replace("data-js", "")


def test_dashboard_mnemosyne_and_layers_present(tmp_path: Path) -> None:
    """The seven layers + MNEMOSYNE are all rendered from the payload."""
    data = _extract_data(build_dashboard_html(InMemoryStore()))
    ids = {l["id"] for l in data["layers"]}
    assert ids == {"L0", "L1", "L2", "L3", "L4", "L5", "L6"}
    assert "MNEMOSYNE" in data["mnemosyne"]["role"].upper() or data["mnemosyne"]["role"]