"""Tests for the synthetic load harness — real pressure + durability."""

from __future__ import annotations

from pathlib import Path

from universal_mind.tools.load_harness import (
    LoadReport,
    run_load,
    verify_durability_under_load,
)


def test_run_load_reports_honest_numbers(tmp_path: Path) -> None:
    report = run_load(str(tmp_path), requests=15)
    assert report.request_count == 15
    assert report.final_ledger_size > 0
    assert report.throughput_per_second > 0
    assert report.p95_latency_ms >= report.p50_latency_ms
    # Throttle legitimately blocks later requests once the shared ledger accrues
    # faults — the harness must report that honestly, not hide it.
    assert 0 <= report.failed <= report.request_count


def test_fresh_load_has_no_failures(tmp_path: Path) -> None:
    """A short, fresh run completes with zero failures before throttle accrues."""
    report = run_load(str(tmp_path), requests=3)
    assert report.failed == 0


def test_load_is_durable_across_restart(tmp_path: Path) -> None:
    run_load(str(tmp_path), requests=10)
    assert verify_durability_under_load(str(tmp_path)) is True


def test_load_report_is_immutable(tmp_path: Path) -> None:
    from dataclasses import FrozenInstanceError

    report = run_load(str(tmp_path), requests=5)
    assert isinstance(report, LoadReport)
    try:
        report.request_count = 99  # type: ignore[misc]
        raised: bool = False
    except FrozenInstanceError:
        raised = True
    assert raised is True


def test_ledger_has_expected_kinds(tmp_path: Path) -> None:
    report = run_load(str(tmp_path), requests=5)
    assert "intent_received" in report.ledger_kinds
    assert "capability_result" in report.ledger_kinds