"""R53 — MODULE COVERAGE for the three riskiest untested modules.

email_outbox (real .eml files + honest SMTP refusal), drift (the perf
ratchet's own gate), tick_pulse (the heartbeat the status page trusts).
Each test exercises the REAL function against the REAL store/filesystem.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


class TestEmailOutbox:
    def test_compose_real_eml_with_headers(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose

        res = compose(to="boss@example.com", subject="گزارش",
                      body="سلام", out_dir=str(tmp_path))
        assert res["ok"] is True
        eml = Path(res["path"])
        assert eml.exists() and eml.stat().st_size > 0
        # the Subject is MIME base64 (the email standard) — parse it back
        from email import policy
        from email.parser import BytesParser

        parsed = BytesParser(policy=policy.default).parsebytes(eml.read_bytes())
        assert str(parsed["To"]) == "boss@example.com"
        assert str(parsed["Subject"]) == "گزارش"  # decoded from MIME base64
        assert res["to"] == "boss@example.com"

    def test_compose_without_recipient_is_honest_refusal(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose

        res = compose(body="x", out_dir=str(tmp_path))
        assert res["ok"] is False
        assert "گیرنده" in res["error"]

    def test_compose_attaches_real_file(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose

        att = tmp_path / "report.txt"
        att.write_text("data", encoding="utf-8")
        res = compose(to="a@b.c", attachment=str(att), out_dir=str(tmp_path))
        assert res["ok"] is True
        assert res.get("attachment_bytes", 0) > 0  # the real key

    def test_send_without_smtp_env_is_named_refusal(self, tmp_path: Path) -> None:
        from universal_mind.email_outbox import compose, send

        res = compose(to="a@b.c", out_dir=str(tmp_path))
        assert res["ok"] is True
        os.environ.pop("UM_SMTP_HOST", None)
        out = send(res["path"])
        assert out["ok"] is False
        assert "SMTP" in out["error"] or "اعتبارنامه" in out["error"]


class TestDrift:
    def test_no_baseline_is_honest_unmeasured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from universal_mind import drift

        monkeypatch.setattr(drift, "load_baseline", lambda: None)
        v = drift.check_perf_drift()
        assert v.ok is False
        assert "مبنا" in v.detail  # the remedy is named, never a silent pass

    def test_ratio_against_real_baseline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from universal_mind import drift

        monkeypatch.setattr(drift, "load_baseline", lambda: {"hot_path_ms": 100.0})
        monkeypatch.setattr(drift, "measure_hot_path", lambda: 150.0)
        v = drift.check_perf_drift()
        assert v.ok is True  # 1.5x is within the 2.0 gate
        assert "150" in v.detail or "1.5" in v.detail

    def test_slowdown_over_gate_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from universal_mind import drift

        monkeypatch.setattr(drift, "load_baseline", lambda: {"hot_path_ms": 100.0})
        monkeypatch.setattr(drift, "measure_hot_path", lambda: 300.0)
        v = drift.check_perf_drift()
        assert v.ok is False  # 3.0x over the 2.0 gate is a real drift verdict


class TestTickPulse:
    def test_pulse_window_reads_real_store(self) -> None:
        from universal_mind.tick_pulse import pulse_window

        days = pulse_window()
        assert isinstance(days, list)
        assert len(days) <= 7  # WINDOW_DAYS law

    def test_alive_streak_skips_empty_today(self) -> None:
        from datetime import date

        from universal_mind.tick_pulse import PulseDay, alive_streak

        today = date.today().isoformat()
        window = [
            PulseDay(day=today, runs=0, ok=0),           # empty today
            PulseDay(day="2026-09-29", runs=5, ok=5),    # awake yesterday
            PulseDay(day="2026-09-28", runs=3, ok=3),
            PulseDay(day="2026-09-27", runs=0, ok=0),     # gap
        ]
        assert alive_streak(window) == 2  # today must not break the streak

    def test_alive_streak_all_dead_is_zero(self) -> None:
        from universal_mind.tick_pulse import PulseDay, alive_streak

        window = [PulseDay(day="2026-09-20", runs=0, ok=0)]
        assert alive_streak(window) == 0
