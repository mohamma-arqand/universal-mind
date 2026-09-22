"""Tests: R44 item 5 — the cross-examiner (independent second numeric verdict).

Live laws:
1. The second opinion is INDEPENDENT: pure Python over the same series —
   agreement on a real run (the production numpy path vs the reducer).
2. A disagreement is a CAUGHT BUG, named — never silent.
3. The Persian report SPEAKS the cross-exam (agreement = second signature,
   disagreement = the field and both values).
4. Unsupported shapes say 'skipped', never lie.
"""

from __future__ import annotations

from typing import Any


class TestPureStats:
    """The independent reducer itself."""

    def test_pure_python_matches_statistics_module(self) -> None:
        from universal_mind.cross_examiner import pure_stats

        out = pure_stats([4.0, 6.0, 9.0])
        assert out is not None
        assert abs(out["mean"] - 6.333333333333333) < 1e-9
        assert out["count"] == 3.0
        assert out["min"] == 4.0 and out["max"] == 9.0

    def test_none_on_unexaminable_shapes(self) -> None:
        from universal_mind.cross_examiner import pure_stats

        assert pure_stats("not a series") is None
        assert pure_stats([]) is None


class TestCrossExamine:
    """The comparison over a real stats payload."""

    def test_agreement_on_a_real_payload(self) -> None:
        from universal_mind.cross_examiner import cross_examine

        payload = {"mean": 6.333333333333333, "std": 2.0548046676563256,
                   "min": 4.0, "max": 9.0, "median": 6.0, "count": 3,
                   "_series": [4.0, 6.0, 9.0]}
        exam = cross_examine(payload)["cross_exam"]
        assert exam["status"] == "agree"

    def test_disagreement_is_a_caught_bug(self) -> None:
        from universal_mind.cross_examiner import cross_examine

        payload = {"mean": 7.0, "std": 2.0, "min": 4.0, "max": 9.0,
                   "median": 6.0, "count": 3, "_series": [4.0, 6.0, 9.0]}
        exam = cross_examine(payload)["cross_exam"]
        assert exam["status"] == "disagree"
        assert exam["field"] == "mean"
        assert exam["numpy"] == 7.0

    def test_skipped_when_no_numbers(self) -> None:
        from universal_mind.cross_examiner import cross_examine

        exam = cross_examine({"ok": True})["cross_exam"]
        assert exam["status"] == "skipped"


class TestTheRealChainSpeaks:
    """The production path: route → data → the report names the cross-exam."""

    def test_real_run_carries_the_cross_exam(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-5.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                                classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("میانگین ۴ و ۶ و ۹ را حساب کن")
        assert p["ok"] is True
        exam: Any = p["result"]["data"].get("cross_exam")
        assert isinstance(exam, dict) and exam.get("status") == "agree"

    def test_the_report_speaks_the_cross_exam(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "r44-5b.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent",
                                classmethod(lambda cls: iso)):
            from universal_mind.persian_router import route_and_run

            p = route_and_run("میانگین ۴ و ۶ و ۹ را حساب کن")
        assert "داور متقاطع عددی" in (p.get("agent_report") or "")

    def test_disagreement_is_named_in_the_report(self) -> None:
        from universal_mind.cross_examiner import persian_note

        note = persian_note({"status": "disagree", "field": "mean",
                             "numpy": 7.0, "pure": 6.333})
        assert note is not None and "mean" in note and "باگ" in note
