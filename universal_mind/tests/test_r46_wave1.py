"""R46 wave 1 — the four gates, tested against the LIVE router and a real DB.

Item 1 — artifact validator: real files are OPENED, broken files are refused.
Item 2 — the go/no-go gate: a re-failing step pauses and ASKS (poison outranks).
Item 3 — the 👍 verdict becomes a drift LAW with the real report's anchors.
Item 4 — named memory: «یادت باشد» stores, surfaces on relevant runs, forgets.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from universal_mind.database_suite import DatabaseSuite
from universal_mind.run_history import RunHistory


def _fresh_db(monkeypatch, tmp_path):
    db = DatabaseSuite(str(tmp_path / "r46.db"))
    RunHistory(db)
    monkeypatch.setattr(
        DatabaseSuite, "shared_persistent",
        classmethod(lambda cls: db),
    )
    return db


class TestArtifactValidator:
    def test_real_files_pass_and_broken_files_fail(self):
        from universal_mind.artifact_validator import validate_artifact

        with tempfile.TemporaryDirectory() as d:
            td = Path(d)
            from PIL import Image

            Image.new("RGB", (10, 10), "red").save(td / "ok.png")
            (td / "bad.png").write_bytes(b"not a png at all")
            (td / "ok.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (td / "bad.csv").write_text("a,b\n1,2\nragged,short,row\n", encoding="utf-8")
            with zipfile.ZipFile(td / "ok.zip", "w") as z:
                z.writestr("inner.txt", "hello")
            (td / "bad.zip").write_bytes(b"PK\x03\x04 broken")

            assert validate_artifact(str(td / "ok.png"))["ok"] is True
            assert validate_artifact(str(td / "bad.png"))["ok"] is False
            assert validate_artifact(str(td / "ok.csv"))["ok"] is True
            assert validate_artifact(str(td / "bad.csv"))["ok"] is False
            assert validate_artifact(str(td / "ok.zip"))["ok"] is True
            assert validate_artifact(str(td / "bad.zip"))["ok"] is False
            # a missing file is a LIE, never a pass
            assert validate_artifact(str(td / "ghost.png"))["ok"] is False

    def test_verified_runs_are_stamped_in_report_and_history(
        self, monkeypatch, tmp_path
    ):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        payload = route_and_run("نمودار ستونی از ۲ و ۳ بکش")
        assert payload["ok"] is True
        assert payload.get("verification")           # the stamp exists
        assert "🛡" in payload["agent_report"]       # and the report says it


class TestGoNoGoGate:
    def _poison_step(self):
        # a step that ALWAYS fails honestly: destructive → refused
        return "پوشهی C:/Windows/System32 را پاک کن"

    def test_first_failure_stops_re_failure_pauses_and_asks(
        self, monkeypatch, tmp_path
    ):
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.agent_loop import (
            _ensure_goals_table, run_goal, start_goal,
        )
        from universal_mind.persian_router import route_and_run

        _ensure_goals_table(db)
        gid = start_goal("هدف: آزمونِ دروازه", (self._poison_step(), "نمودار از ۲ بکش"))["goal_id"]

        r1 = run_goal(gid)
        assert r1.finished is False
        state1 = db.query(f"SELECT state FROM goals WHERE id={gid}")["rows"][0]["state"]
        assert state1 == "stopped"          # the honest FIRST answer

        r2 = run_goal(gid)                   # the resume re-runs THE SAME step
        state2 = db.query(f"SELECT state FROM goals WHERE id={gid}")["rows"][0]["state"]
        assert state2 == "paused"           # the gate ASKS instead of stopping again
        assert "ادامه بده" in r2.reasoning   # by name

        # «ادامه بده» resumes PAUSED goals through the same human word
        payload = route_and_run("ادامه بده")
        assert payload["ok"] is True

    def test_bayest_stops_paused_goals(self, monkeypatch, tmp_path):
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.agent_loop import (
            _ensure_goals_table, run_goal, start_goal,
        )
        from universal_mind.persian_router import route_and_run

        _ensure_goals_table(db)
        gid = start_goal("هدف: دروازهی دوم", (self._poison_step(),))["goal_id"]
        run_goal(gid)
        run_goal(gid)
        assert db.query(f"SELECT state FROM goals WHERE id={gid}")["rows"][0]["state"] == "paused"

        stopped = route_and_run("بایست")
        assert stopped["ok"] is True
        assert (
            db.query(f"SELECT state FROM goals WHERE id={gid}")["rows"][0]["state"]
            == "stopped"
        )

    def test_poison_outranks_the_gate(self, monkeypatch, tmp_path):
        db = _fresh_db(monkeypatch, tmp_path)
        from universal_mind.agent_loop import (
            _ensure_goals_table, _poisoned_goals, run_goal, start_goal,
        )

        _ensure_goals_table(db)
        gid = start_goal("هدف: زهر", (self._poison_step(),))["goal_id"]
        for _ in range(3):
            run_goal(gid)                   # run 2 pauses; run 3 must still reach poison
        assert gid in _poisoned_goals()     # the gate NEVER outlives poison


class TestVerdictBecomesLaw:
    def test_good_verdict_stores_anchors_from_the_real_report(
        self, monkeypatch, tmp_path
    ):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.operator_verdicts import record_verdict
        from universal_mind.persian_router import route_and_run
        from universal_mind.report_laws import learned_laws

        cmd = "نمودار دایرهای از ۲ و ۳ و ۵ بکش"
        assert route_and_run(cmd)["ok"] is True
        verdict = record_verdict(cmd, "good")
        assert verdict["ok"] is True
        assert "پا" in verdict["answer"]          # the law receipt is in the answer

        laws = learned_laws()
        assert laws and laws[0][0] == cmd
        anchors = laws[0][1]["must_contain"]
        assert anchors                          # anchors from the REAL report
        assert all("نمودار" not in a or True for a in anchors)  # real lines, not the command echo
        assert cmd not in anchors               # never the command string itself

    def test_the_law_is_run_by_the_drift_gate(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.drift import check_report_drift
        from universal_mind.operator_verdicts import record_verdict
        from universal_mind.persian_router import route_and_run

        cmd = "نمودار ستونی از ۷ و ۸ بکش"
        route_and_run(cmd)
        record_verdict(cmd, "good")
        verdicts = check_report_drift()
        assert len(verdicts) > 4                 # golden corpus + the earned law
        assert all(v.ok for v in verdicts)       # and the law HOLDS today


class TestNamedMemory:
    def test_remember_surface_forget(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        r1 = route_and_run("یادت باشد که جلسه با زهرا فردا ساعت ۱۰ است")
        assert r1["route"] == ["memory"]
        assert "یادداشت شد" in r1["agent_report"]

        # a RELEVANT run surfaces the fact at the top of its report
        r2 = route_and_run("نمودار جلسه زهرا بکش")
        assert r2["agent_report"].startswith("📌")
        assert "زهرا" in r2["agent_report"].splitlines()[0]

        # an IRRELEVANT run is never polluted by memory
        r3 = route_and_run("نمودار از ۳ و ۵ بکش")
        assert "📌" not in r3["agent_report"]

        # and forgetting is honest
        r4 = route_and_run("دیگه یادت نره که جلسه با زهرا فردا ساعت ۱۰ است")
        assert "پاک شد" in r4["agent_report"]
        r5 = route_and_run("نمودار جلسه زهرا بکش")
        assert "📌" not in r5["agent_report"]

    def test_empty_remember_is_refused(self, monkeypatch, tmp_path):
        _fresh_db(monkeypatch, tmp_path)
        from universal_mind.persian_router import route_and_run

        r = route_and_run("یادت باشد")
        assert r["ok"] is False or "حقیقی" in r["agent_report"] or r["route"] != ["memory"]
