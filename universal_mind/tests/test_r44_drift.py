"""Tests: R44 item 14 — the drift detector (slow rot becomes loud).

Live laws:
1. Performance drift is RELATIVE: a machine-independent ratio vs the
   committed baseline, and a 2× slowdown goes red.
2. The baseline is never silently rewritten — a gate read it, a human
   (or their explicit act) refreshes it.
3. No baseline = honest refusal, never a silent pass.
4. Report laws are pinned by a golden corpus: a vanished promise or a
   new leak is drift even though unit tests still pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

import universal_mind.drift as drift


def _fake_gate(ms_now: float, base_ms: float) -> Any:
    """check_perf_drift with the measurement stubbed and a planted baseline."""
    with mock_patch.object(drift, "measure_hot_path", lambda: ms_now), \
         mock_patch.object(drift, "load_baseline", lambda: {"hot_path_ms": base_ms}):
        return drift.check_perf_drift()


class TestPerfDrift:
    def test_a_2x_slowdown_is_red(self) -> None:
        v = _fake_gate(ms_now=200.0, base_ms=100.0)
        assert v.ok is False
        assert "2.00" in v.detail

    def test_normal_variance_is_green(self) -> None:
        v = _fake_gate(ms_now=130.0, base_ms=100.0)
        assert v.ok is True

    def test_a_faster_machine_is_green_not_negative_drift(self) -> None:
        v = _fake_gate(ms_now=40.0, base_ms=100.0)
        assert v.ok is True and "0.40" in v.detail

    def test_no_baseline_is_an_honest_refusal(self) -> None:
        with mock_patch.object(drift, "measure_hot_path", lambda: 90.0), \
             mock_patch.object(drift, "load_baseline", lambda: None):
            v = drift.check_perf_drift()
        assert v.ok is False and "خط مبنا" in v.detail

    def test_the_real_baseline_file_exists_and_is_sane(self) -> None:
        # the committed contract: a real number, not a placeholder
        path = Path(drift.__file__).parent / "perf_baseline.json"
        assert path.exists(), "the baseline must be committed, not ephemeral"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert 0 < float(data["hot_path_ms"]) < 5000
        assert data["command"] == drift.HOT_COMMAND

    def test_write_baseline_records_the_truth(self, tmp_path: Path) -> None:
        with mock_patch.object(drift, "BASELINE_PATH", tmp_path / "b.json"):
            payload = drift.write_baseline(123.4)
        assert payload["hot_path_ms"] == 123.4
        assert (tmp_path / "b.json").exists()


class TestReportDrift:
    def test_a_vanished_promise_is_drift(self) -> None:
        corpus = [("سلام", {"must_contain": ["هرگزچنینوعده‌ای‌نیست"],
                            "must_not_contain": []})]
        with mock_patch.object(drift, "GOLDEN_REPORT_CORPUS", corpus):
            verdicts = drift.check_report_drift()
        assert len(verdicts) == 1 and verdicts[0].ok is False

    def test_a_new_leak_is_drift(self) -> None:
        corpus = [("خدانگهدار", {"must_contain": [], "must_not_contain": ["منتظر"]})]
        with mock_patch.object(drift, "GOLDEN_REPORT_CORPUS", corpus):
            verdicts = drift.check_report_drift()
        assert verdicts[0].ok is False, verdicts[0].detail

    def test_a_crash_is_drift_not_a_skip(self) -> None:
        def boom(_cmd: str) -> Any:
            raise RuntimeError("reporter died")

        with mock_patch("universal_mind.persian_router.route_and_run", boom), \
             mock_patch.object(drift, "GOLDEN_REPORT_CORPUS", [("سلام", {"must_contain": [], "must_not_contain": []})]):
            verdicts = drift.check_report_drift()
        assert verdicts[0].ok is False and "crashed" in verdicts[0].detail

    def test_the_real_corpus_is_green(self) -> None:
        verdicts = drift.check_report_drift()
        assert verdicts, "the corpus must not be empty"
        bad = [v for v in verdicts if not v.ok]
        assert not bad, [v.detail for v in bad]
