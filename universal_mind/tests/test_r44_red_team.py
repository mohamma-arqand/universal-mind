"""Tests: R44 item 6 — the nightly red team (the platform attacks itself).

Live laws:
1. The hostile corpus passes through the REAL router and every answer is
   graded — an honest sweep is printed, never assumed.
2. A dishonest answer (crash, silent failure, fake success) becomes a
   FINDING: a red_team_findings row + a self-repair goal in the store.
3. The grader itself is exact: a named refusal passes, a silent hole fails.
"""

from __future__ import annotations

from typing import Any


class TestTheGrader:
    """grade_answer — the exact lens."""

    def test_named_refusal_is_honest(self) -> None:
        from universal_mind.red_team import grade_answer

        g = grade_answer("نمادار بکش", {"ok": False, "agent_report": "فرمان مبهم است"}, None)
        assert g["honest"] is True and g["kind"] == "named-refusal"

    def test_crash_is_a_finding(self) -> None:
        from universal_mind.red_team import grade_answer

        g = grade_answer("x", {}, "ValueError: boom")
        assert g["honest"] is False and g["kind"] == "crash"

    def test_silent_failure_is_a_finding(self) -> None:
        from universal_mind.red_team import grade_answer

        g = grade_answer("x", {"ok": False, "agent_report": "", "errors": {}}, None)
        assert g["honest"] is False and g["kind"] == "silent-failure"

    def test_fake_success_is_a_finding(self) -> None:
        from universal_mind.red_team import grade_answer

        g = grade_answer("x", {"ok": True, "result": {}, "agent_report": ""}, None)
        assert g["honest"] is False and g["kind"] == "fake-success"

    def test_real_answer_is_honest(self) -> None:
        from universal_mind.red_team import grade_answer

        g = grade_answer("x", {"ok": True, "result": {"data": {"mean": 5}}, "agent_report": "انجام شد"}, None)
        assert g["honest"] is True


class TestTheSweep:
    """run_red_team over the REAL router (isolated store)."""

    def test_the_corpus_is_fixed_and_versioned(self) -> None:
        from universal_mind.red_team import HOSTILE_CORPUS

        assert len(HOSTILE_CORPUS) >= 8  # every attack class present
        assert any("ignore all previous" in c for c in HOSTILE_CORPUS)  # injection
        assert any(not c.strip() for c in HOSTILE_CORPUS)  # empty
        assert any("پاک کن" in c for c in HOSTILE_CORPUS)  # destructive

    def test_sweep_reports_every_line(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "rt.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            from universal_mind.red_team import run_red_team

            out: Any = run_red_team(store=iso)
        assert out["total"] == len(out.get("findings", [])) + out["honest"]

    def test_a_finding_becomes_a_self_repair_goal(self) -> None:
        """Inject a saboteur: one corpus line must CRASH. The sweep catches it
        and files the goal — the whole loop, proven with a real injected bug."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        import universal_mind.persian_router as pr
        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "rt2.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            with mock_patch.object(
                pr, "route_and_run",
                side_effect=[{"ok": False, "agent_report": "مبهم"}] * 7 + [RuntimeError("saboteur")],
            ) if False else _crashing_router(pr, mock_patch):
                from universal_mind.red_team import run_red_team

                out = run_red_team(store=iso)
            assert out["findings"], "the sabotage must be caught"
            kinds = {f["kind"] for f in out["findings"]}
            assert "crash" in kinds
            rows = iso.query("SELECT goal FROM goals")["rows"]
            assert rows and "red-team" in str(rows[0]["goal"])

    def test_honest_sweep_files_nothing(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch as mock_patch

        from universal_mind.database_suite import DatabaseSuite

        iso = DatabaseSuite(str(Path(tempfile.mkdtemp()) / "rt3.db"))
        with mock_patch.object(DatabaseSuite, "shared_persistent", classmethod(lambda cls: iso)):
            from universal_mind.red_team import run_red_team

            out = run_red_team(store=iso)
        # on a healthy platform: zero findings, zero goals filed
        assert out["findings"] == []


def _crashing_router(pr: Any, mock_patch: Any) -> Any:
    """One corpus line crashes — the honest rest answer as usual."""
    real = pr.route_and_run

    def _fake(cmd: str, *a: Any, **kw: Any) -> Any:
        if "میانگین هیچی" in cmd:
            raise RuntimeError("saboteur")
        return real(cmd, *a, **kw)

    return mock_patch.object(pr, "route_and_run", side_effect=_fake)
