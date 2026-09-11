"""Tests for the continuous self-code-audit."""

from __future__ import annotations

from pathlib import Path

from universal_mind.core.self_code_audit import (
    CodeAuditReport,
    run_self_audit,
    scan_source,
)
from universal_mind.memory.store import InMemoryStore


def test_scan_finds_empty_module(tmp_path: Path) -> None:
    (tmp_path / "empty.py").write_text('"""just a docstring"""\n', encoding="utf-8")
    findings = scan_source(tmp_path)
    assert any(f.kind == "empty_module" for f in findings)


def test_scan_finds_orphaned_import(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text(
        '"""module"""\nfrom universal_mind.telemetry import errors\n', encoding="utf-8"
    )
    findings = scan_source(tmp_path)
    assert any(f.kind == "orphaned_import" for f in findings)


def test_scan_finds_missing_docstring(tmp_path: Path) -> None:
    (tmp_path / "nodoc.py").write_text("x = 1\n", encoding="utf-8")
    findings = scan_source(tmp_path)
    assert any(f.kind == "no_docstring" for f in findings)


def test_clean_module_has_no_findings(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text('"""A clean module."""\ndef f() -> int:\n    return 1\n', encoding="utf-8")
    findings = scan_source(tmp_path)
    assert all(f.path != "ok.py" for f in findings)


def test_run_self_audit_records_to_ledger(tmp_path: Path) -> None:
    (tmp_path / "emptymod.py").write_text('"""only docs"""\n', encoding="utf-8")
    store = InMemoryStore()
    report = run_self_audit(tmp_path, store=store)
    assert report.ledger_record_id is not None
    kinds = [r.get("kind") for r in store.read_all()]
    assert "self_code_audit" in kinds


def test_report_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = CodeAuditReport((), True, 1)
    try:
        r.clean = False  # type: ignore[misc]
        mutated = False
    except FrozenInstanceError:
        mutated = True
    assert mutated is True